#!/usr/bin/env python3
import os
import sys
import numpy as np
import logging
import torch
from tqdm import tqdm
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Set up environment
load_dotenv()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')

# Import Django after setting environment
import django
django.setup()

# Import models after Django setup
from transactions.models import Transaction, Supplier

# Globals to store embeddings and related data
supplier_embeddings = []
supplier_info = []

class Command(BaseCommand):
    help = 'Match transactions without suppliers to similar transactions with suppliers using embeddings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of transactions to process'
        )
        parser.add_argument(
            '--batch',
            type=int,
            default=25,
            help='Batch size for processing'
        )
        parser.add_argument(
            '--threshold',
            type=float,
            default=0.8,
            help='Similarity threshold (0-1) for matching'
        )
        parser.add_argument(
            '--min-examples',
            type=int,
            default=2,
            help='Minimum number of examples needed per supplier'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without updating the database'
        )

    def handle(self, *args, **options):
        try:
            # Try to import required packages
            try:
                from sentence_transformers import SentenceTransformer, util
            except ImportError:
                self.stderr.write(
                    "Required packages not installed. Please run: "
                    "pip install sentence-transformers torch"
                )
                return
            
            limit = options['limit']
            batch_size = options['batch']
            threshold = options['threshold']
            min_examples = options['min_examples']
            dry_run = options['dry_run']
            
            logger.info(f"Starting supplier matching with embeddings (limit={limit}, threshold={threshold})")
            
            # Load model
            logger.info("Loading sentence transformer model...")
            model = SentenceTransformer('all-MiniLM-L6-v2')
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            logger.info(f"Using device: {device}")
            model = model.to(device)
            
            # Create reference database from transactions with suppliers
            self._build_reference_db(model, min_examples)
            
            # Get transactions without suppliers
            unmatched_txs = self._get_unmatched_transactions(limit)
            
            if not unmatched_txs:
                logger.info("No unmatched transactions found.")
                return
                
            logger.info(f"Found {len(unmatched_txs)} unmatched transactions to process")
            
            # Process in batches
            total_matched = 0
            
            for i in range(0, len(unmatched_txs), batch_size):
                batch = unmatched_txs[i:i+batch_size]
                matched = self._process_batch(model, batch, threshold, dry_run)
                total_matched += matched
                
            logger.info(f"Processing complete. {total_matched} transactions matched to suppliers.")
                
        except Exception as e:
            logger.exception(f"Error in supplier matching: {e}")
            self.stderr.write(f"Error: {e}")
            
    def _build_reference_db(self, model, min_examples):
        """Build a reference database of embeddings from transactions with known suppliers."""
        global supplier_embeddings, supplier_info
        
        # Get suppliers with at least min_examples transactions
        suppliers_with_min_txs = Transaction.objects.values('supplier_id')\
            .annotate(count=Count('supplier_id'))\
            .filter(count__gte=min_examples, supplier__isnull=False)\
            .values_list('supplier_id', flat=True)
            
        if not suppliers_with_min_txs:
            logger.warning("No suppliers with sufficient transaction examples found.")
            return
            
        logger.info(f"Found {len(suppliers_with_min_txs)} suppliers with at least {min_examples} transactions")
        
        # Clear global variables
        supplier_embeddings = []
        supplier_info = []
        
        # Process each supplier
        for supplier_id in tqdm(suppliers_with_min_txs, desc="Building reference database"):
            # Get supplier info
            supplier = Supplier.objects.get(id=supplier_id)
            
            # Get this supplier's transactions
            txs = Transaction.objects.filter(supplier_id=supplier_id)\
                .values_list('description', flat=True)
                
            # Convert to list and get embeddings
            descriptions = list(txs)
            embeddings = model.encode(descriptions, convert_to_tensor=True)
            
            # Add to our reference database
            for i, embedding in enumerate(embeddings):
                supplier_embeddings.append(embedding)
                supplier_info.append({
                    'supplier_id': supplier_id,
                    'supplier_name': supplier.name,
                    'description': descriptions[i]
                })
                
        logger.info(f"Reference database built with {len(supplier_embeddings)} transaction embeddings")
        
        # Convert list to tensor for faster processing
        supplier_embeddings = torch.stack(supplier_embeddings)
    
    def _get_unmatched_transactions(self, limit):
        """Get transactions without suppliers."""
        return list(Transaction.objects.filter(
            supplier__isnull=True,
            is_internal_transfer=False,  # Skip internal transfers
            is_wage_transfer=False,      # Skip wage transfers
            is_tax_transfer=False,       # Skip tax transfers
            is_forbidden=False,          # Skip forbidden transactions
        ).order_by('-date')[:limit].values('id', 'description', 'amount', 'date'))
    
    def _process_batch(self, model, batch, threshold, dry_run):
        """Process a batch of unmatched transactions."""
        global supplier_embeddings, supplier_info
        
        # Import required libraries for this method
        from sentence_transformers import util
        
        if len(supplier_embeddings) == 0:
            logger.warning("Reference database is empty. Cannot match transactions.")
            return 0
            
        # Get descriptions for the batch
        descriptions = [tx['description'] for tx in batch]
        
        # Encode descriptions
        batch_embeddings = model.encode(descriptions, convert_to_tensor=True)
        
        # Match against supplier embeddings
        matched_count = 0
        
        for i, embedding in enumerate(batch_embeddings):
            # Compute cosine similarity
            cosine_scores = util.cos_sim(embedding, supplier_embeddings)[0]
            
            # Get best match
            best_score, best_idx = torch.max(cosine_scores, dim=0)
            best_score = best_score.item()
            best_idx = best_idx.item()
            
            tx = batch[i]
            
            if best_score >= threshold:
                match_info = supplier_info[best_idx]
                
                # Log the match
                logger.info(f"Match found (score: {best_score:.4f}):")
                logger.info(f"  Transaction: {tx['description']}")
                logger.info(f"  Best match: {match_info['description']}")
                logger.info(f"  Supplier: {match_info['supplier_name']}")
                
                if not dry_run:
                    # Update the transaction with the matched supplier
                    Transaction.objects.filter(id=tx['id']).update(
                        supplier_id=match_info['supplier_id']
                    )
                    matched_count += 1
            else:
                logger.debug(f"No good match for: {tx['description']} (best score: {best_score:.4f})")
                
        if dry_run:
            logger.info(f"Dry run - would have updated {matched_count} transactions")
        else:
            logger.info(f"Updated {matched_count} transactions with supplier matches")
            
        return matched_count

if __name__ == "__main__":
    pass 