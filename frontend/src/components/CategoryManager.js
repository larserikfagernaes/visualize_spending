import React, { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Box,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Divider
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import axios from 'axios';

const API_URL = 'http://localhost:8000/api/v1';
// Create encoded credentials
const authCredentials = btoa('dev:dev');

const CategoryManager = ({ categories = [], onCategoryUpdate }) => {
  const [newCategory, setNewCategory] = useState({ name: '', description: '' });
  const [editCategory, setEditCategory] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  
  // Ensure categories is always an array
  const categoriesList = Array.isArray(categories) ? categories : [];

  // Default request configuration with authentication
  const requestConfig = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Basic ${authCredentials}`
    },
    withCredentials: true
  };

  const handleAddCategory = async () => {
    try {
      console.log('Adding new category:', newCategory);
      const response = await axios.post(`${API_URL}/categories/`, newCategory, requestConfig);
      console.log('Category added successfully:', response.data);
      setNewCategory({ name: '', description: '' });
      if (onCategoryUpdate) {
        console.log('Calling onCategoryUpdate to refresh categories list');
        onCategoryUpdate();
      }
    } catch (error) {
      console.error('Error adding category:', error);
      console.error('Response data:', error.response?.data);
    }
  };

  const handleUpdateCategory = async () => {
    try {
      const response = await axios.put(`${API_URL}/categories/${editCategory.id}/`, editCategory, requestConfig);
      console.log('Category updated successfully:', response.data);
      setDialogOpen(false);
      if (onCategoryUpdate) onCategoryUpdate();
    } catch (error) {
      console.error('Error updating category:', error);
      console.error('Response data:', error.response?.data);
    }
  };

  const handleDeleteCategory = async (id) => {
    try {
      await axios.delete(`${API_URL}/categories/${id}/`, requestConfig);
      console.log('Category deleted successfully');
      if (onCategoryUpdate) onCategoryUpdate();
    } catch (error) {
      console.error('Error deleting category:', error);
      console.error('Response data:', error.response?.data);
    }
  };

  const openEditDialog = (category) => {
    setEditCategory(category);
    setDialogOpen(true);
  };

  return (
    <>
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Add New Category
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Category Name"
              variant="outlined"
              value={newCategory.name}
              onChange={(e) => setNewCategory({ ...newCategory, name: e.target.value })}
              fullWidth
            />
            <TextField
              label="Description"
              variant="outlined"
              value={newCategory.description}
              onChange={(e) => setNewCategory({ ...newCategory, description: e.target.value })}
              fullWidth
              multiline
              rows={2}
            />
            <Button
              variant="contained"
              onClick={handleAddCategory}
              disabled={!newCategory.name}
            >
              Add Category
            </Button>
          </Box>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Manage Categories
          </Typography>
          <List>
            {categoriesList.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No categories found
              </Typography>
            ) : (
              categoriesList.map((category) => (
                <React.Fragment key={category.id}>
                  <ListItem
                    secondaryAction={
                      <Box>
                        <IconButton edge="end" onClick={() => openEditDialog(category)}>
                          <EditIcon />
                        </IconButton>
                        <IconButton edge="end" onClick={() => handleDeleteCategory(category.id)}>
                          <DeleteIcon />
                        </IconButton>
                      </Box>
                    }
                  >
                    <ListItemText
                      primary={category.name}
                      secondary={category.description}
                    />
                  </ListItem>
                  <Divider component="li" />
                </React.Fragment>
              ))
            )}
          </List>
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>Edit Category</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Category Name"
              variant="outlined"
              value={editCategory?.name || ''}
              onChange={(e) => setEditCategory({ ...editCategory, name: e.target.value })}
              fullWidth
            />
            <TextField
              label="Description"
              variant="outlined"
              value={editCategory?.description || ''}
              onChange={(e) => setEditCategory({ ...editCategory, description: e.target.value })}
              fullWidth
              multiline
              rows={2}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleUpdateCategory} variant="contained">Save</Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default CategoryManager; 