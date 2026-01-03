// I'm Bored - Single Page App

let allActivities = {};
let currentType = null; // null means "all"

// ===== INITIALIZATION =====

document.addEventListener('DOMContentLoaded', () => {
    loadActivities();

    // Set up form submission
    const form = document.getElementById('addActivityForm');
    if (form) {
        form.addEventListener('submit', addActivity);
    }
});

// ===== DATA LOADING =====

async function loadActivities() {
    try {
        const response = await fetch('/api/activities');
        const data = await response.json();

        if (data.success) {
            allActivities = data.activities;
            renderSidebar();
            renderBottomNav();
            renderActivities();
        }
    } catch (error) {
        console.error('Error loading activities:', error);
        showNotification('Error loading activities', 'error');
    }
}

// ===== SIDEBAR NAVIGATION =====

function renderSidebar() {
    const nav = document.getElementById('sidebarNav');
    if (!nav) return;

    nav.innerHTML = '';

    // Add "All" item
    const allItem = document.createElement('div');
    allItem.className = 'nav-item' + (currentType === null ? ' active' : '');
    allItem.textContent = 'All';
    allItem.onclick = () => selectType(null);

    const totalCount = Object.values(allActivities).reduce((sum, activities) => sum + activities.length, 0);
    const countSpan = document.createElement('span');
    countSpan.className = 'nav-item-count';
    countSpan.textContent = totalCount;
    allItem.appendChild(countSpan);

    nav.appendChild(allItem);

    // Add 'todo' first if it exists
    if (allActivities['todo']) {
        const todoItem = document.createElement('div');
        todoItem.className = 'nav-item' + (currentType === 'todo' ? ' active' : '');
        todoItem.textContent = 'To-Do';
        todoItem.onclick = () => selectType('todo');

        const count = allActivities['todo'].length;
        const countSpan = document.createElement('span');
        countSpan.className = 'nav-item-count';
        countSpan.textContent = count;
        todoItem.appendChild(countSpan);

        nav.appendChild(todoItem);
    }

    // Add other type items (sorted, excluding 'todo')
    const types = Object.keys(allActivities)
        .filter(t => t !== 'todo')
        .sort((a, b) => {
            if (a === 'general') return -1;
            if (b === 'general') return 1;
            return a.localeCompare(b);
        });

    types.forEach(type => {
        const item = document.createElement('div');
        item.className = 'nav-item' + (currentType === type ? ' active' : '');
        item.textContent = type;
        item.onclick = () => selectType(type);

        const count = allActivities[type].length;
        const countSpan = document.createElement('span');
        countSpan.className = 'nav-item-count';
        countSpan.textContent = count;
        item.appendChild(countSpan);

        nav.appendChild(item);
    });

    // Add "+ New" button
    const newCategoryBtn = document.createElement('div');
    newCategoryBtn.className = 'nav-item new-category-btn';
    newCategoryBtn.textContent = '+ New Category';
    newCategoryBtn.onclick = createNewCategory;
    nav.appendChild(newCategoryBtn);
}

function renderBottomNav() {
    const bottomNav = document.getElementById('bottomNav');
    if (!bottomNav) return;

    const scrollContainer = bottomNav.querySelector('.bottom-nav-scroll');
    if (!scrollContainer) return;

    scrollContainer.innerHTML = '';

    // Add "All" item
    const totalCount = Object.values(allActivities).reduce((sum, activities) => sum + activities.length, 0);
    const allItem = createBottomNavItem('All', null, totalCount);
    scrollContainer.appendChild(allItem);

    // Add 'todo' first if it exists
    if (allActivities['todo']) {
        const todoItem = createBottomNavItem('To-Do', 'todo', allActivities['todo'].length);
        scrollContainer.appendChild(todoItem);
    }

    // Add other types (sorted, excluding 'todo')
    const types = Object.keys(allActivities)
        .filter(t => t !== 'todo')
        .sort((a, b) => {
            if (a === 'general') return -1;
            if (b === 'general') return 1;
            return a.localeCompare(b);
        });

    types.forEach(type => {
        const count = allActivities[type].length;
        const item = createBottomNavItem(capitalize(type), type, count);
        scrollContainer.appendChild(item);
    });

    // Add "+ New" button
    const newCategoryBtn = document.createElement('div');
    newCategoryBtn.className = 'bottom-nav-item new-category-btn';
    newCategoryBtn.onclick = createNewCategory;
    newCategoryBtn.setAttribute('role', 'button');
    newCategoryBtn.setAttribute('aria-label', 'Create new category');
    newCategoryBtn.textContent = '+ New';
    scrollContainer.appendChild(newCategoryBtn);
}

function createBottomNavItem(label, type, count) {
    const item = document.createElement('div');
    item.className = 'bottom-nav-item' + (currentType === type ? ' active' : '');
    item.onclick = () => selectType(type);
    item.setAttribute('role', 'tab');
    item.setAttribute('aria-selected', currentType === type);
    item.setAttribute('aria-label', `${label}, ${count} items`);

    const labelSpan = document.createElement('span');
    labelSpan.className = 'bottom-nav-label';
    labelSpan.textContent = label + ' ';

    const countSpan = document.createElement('span');
    countSpan.className = 'bottom-nav-count';
    countSpan.textContent = `(${count})`;

    item.appendChild(labelSpan);
    item.appendChild(countSpan);

    return item;
}

function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function selectType(type) {
    currentType = type;
    renderSidebar();
    renderBottomNav();
    renderActivities();
}

// ===== ACTIVITIES DISPLAY =====

function renderActivities() {
    const listDiv = document.getElementById('activitiesList');
    const header = document.getElementById('activitiesHeader');

    if (!listDiv) return;

    // Update header
    if (header) {
        header.textContent = currentType ? `${currentType}` : 'activities';
    }

    // If viewing all, render in grid by category
    if (currentType === null) {
        renderCategoryGrid(listDiv);
        return;
    }

    // Get activities to display for specific type
    const activities = allActivities[currentType] || [];

    // Separate completed and uncompleted
    const uncompleted = activities.filter(a => !a.completed);
    const completed = activities.filter(a => a.completed);

    // Render
    let html = '<ul class="activity-list">';

    if (uncompleted.length === 0 && completed.length === 0) {
        html += '<p style="color: var(--text-secondary); margin-top: 1rem;">No activities found.</p>';
    } else {
        // Uncompleted activities
        uncompleted.forEach(activity => {
            html += renderActivityItem(activity);
        });

        html += '</ul>';

        // Completed section (collapsible)
        if (completed.length > 0) {
            html += `
                <div class="collapsible" id="completedSection">
                    <div class="collapsible-header" onclick="toggleCollapsible('completedSection')">
                        <span class="collapsible-arrow">▶</span>
                        <span>Completed (${completed.length})</span>
                    </div>
                    <div class="collapsible-content">
                        <ul class="activity-list">
            `;

            completed.forEach(activity => {
                html += renderActivityItem(activity);
            });

            html += `
                        </ul>
                    </div>
                </div>
            `;
        }
    }

    listDiv.innerHTML = html;
}

function renderCategoryGrid(listDiv) {
    // Sort types with 'general' first, 'todo' second, then alphabetically
    const sortedTypes = Object.keys(allActivities).sort((a, b) => {
        if (a === 'general') return -1;
        if (b === 'general') return 1;
        if (a === 'todo') return -1;
        if (b === 'todo') return 1;
        return a.localeCompare(b);
    });

    let html = '<div class="category-grid">';

    sortedTypes.forEach(type => {
        const activities = allActivities[type].filter(a => !a.completed);

        if (activities.length === 0) return;

        html += `
            <div class="category-card">
                <div class="category-card-header">${escapeHtml(type)}</div>
                <div class="category-card-content">
        `;

        activities.forEach(activity => {
            html += `
                <div class="activity-grid-item">
                    <span class="activity-id">${activity.id}</span>
                    <span class="activity-grid-description">${escapeHtml(activity.description)}</span>
                </div>
            `;
        });

        html += `
                </div>
            </div>
        `;
    });

    html += '</div>';

    listDiv.innerHTML = html;
}

function renderActivityItem(activity) {
    const isTodo = activity.type === 'todo';

    // Render checkbox for todo items, spacer for non-todo items when viewing All
    const checkboxHtml = isTodo ? `
        <div class="checkbox-wrapper">
            <input
                type="checkbox"
                ${activity.completed ? 'checked' : ''}
                onchange="toggleCompletion(${activity.id}, this.checked)"
            >
            <div class="checkbox-custom"></div>
        </div>
    ` : (currentType === null ? '<div class="checkbox-spacer"></div>' : '');

    // Show type label only when viewing all activities
    const typeLabel = currentType === null ? `<span class="activity-type">${activity.type}</span>` : '';

    return `
        <li class="activity-item ${activity.completed ? 'completed' : ''}">
            <span class="activity-description">${escapeHtml(activity.description)}</span>
            ${typeLabel}
            <button class="delete-btn" data-id="${activity.id}" onclick="handleDelete(event, ${activity.id})">delete</button>
        </li>
    `;
}

function toggleCollapsible(id) {
    const collapsible = document.getElementById(id);
    if (collapsible) {
        collapsible.classList.toggle('open');
    }
}

// ===== RANDOM ACTIVITY (I'M BORED) =====

async function getRandomActivity() {
    const button = document.querySelector('.bored-button');
    const resultDiv = document.getElementById('activityResult');

    button.disabled = true;

    try {
        // Get types to filter by (current selection or all)
        const types = currentType ? [currentType] : null;
        const body = types ? JSON.stringify({ types }) : null;

        const response = await fetch('/get-random-activity', {
            method: 'POST',
            headers: types ? { 'Content-Type': 'application/json' } : {},
            body: body
        });
        const data = await response.json();

        if (data.success) {
            resultDiv.innerHTML = `
                <span class="activity-type">${escapeHtml(data.activity.type)}</span>
                <span>${escapeHtml(data.activity.description)}</span>
            `;
        } else {
            resultDiv.innerHTML = `
                <div class="activity-description" style="color: var(--error);">${escapeHtml(data.message)}</div>
            `;
        }
    } catch (error) {
        resultDiv.innerHTML = `
            <div class="activity-description" style="color: var(--error);">Error fetching activity. Please try again.</div>
        `;
        console.error('Error:', error);
    } finally {
        button.disabled = false;
    }
}

// ===== CRUD OPERATIONS =====

async function createNewCategory() {
    const categoryName = prompt('Enter new category name:');

    if (!categoryName) {
        return; // User cancelled
    }

    const trimmedName = categoryName.trim().toLowerCase();

    if (!trimmedName) {
        showNotification('Category name cannot be empty', 'error');
        return;
    }

    // Check if category already exists
    if (allActivities[trimmedName]) {
        showNotification('Category already exists', 'error');
        return;
    }

    try {
        // Create a placeholder activity to establish the category
        const response = await fetch('/api/activities', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                type: trimmedName,
                description: '(placeholder - feel free to delete or edit)'
            })
        });

        const data = await response.json();

        if (data.success) {
            await loadActivities();
            selectType(trimmedName);
            showNotification('Category created', 'success');
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        console.error('Error creating category:', error);
        showNotification('Error creating category', 'error');
    }
}

async function toggleCompletion(activityId, completed) {
    try {
        const response = await fetch(`/api/activities/${activityId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ completed })
        });

        const data = await response.json();

        if (data.success) {
            await loadActivities();
            showNotification('Activity updated', 'success');
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        console.error('Error updating activity:', error);
        showNotification('Error updating activity', 'error');
    }
}

function handleDelete(event, activityId) {
    event.stopPropagation();
    const button = event.target;

    // Check if button is already in confirm mode
    if (button.classList.contains('confirm-delete')) {
        // Actually delete
        deleteActivity(activityId);
    } else {
        // Reset any other confirm buttons first
        document.querySelectorAll('.delete-btn.confirm-delete').forEach(btn => {
            btn.classList.remove('confirm-delete');
            btn.textContent = 'delete';
        });

        // Enter confirm mode
        button.classList.add('confirm-delete');
        button.textContent = 'are you sure?';

        // Reset after 3 seconds if not clicked
        setTimeout(() => {
            if (button.classList.contains('confirm-delete')) {
                button.classList.remove('confirm-delete');
                button.textContent = 'delete';
            }
        }, 3000);
    }
}

async function deleteActivity(activityId) {
    try {
        const response = await fetch(`/api/activities/${activityId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            await loadActivities();
            showNotification('Activity deleted', 'success');
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        console.error('Error deleting activity:', error);
        showNotification('Error deleting activity', 'error');
    }
}

async function addActivity(event) {
    event.preventDefault();

    const descriptionInput = document.getElementById('activityDescription');
    const description = descriptionInput.value.trim();

    if (!description) {
        showNotification('Please enter a description', 'error');
        return;
    }

    // Use the currently selected type, or 'general' if "All" is selected
    const activityType = currentType || 'general';

    try {
        const response = await fetch('/api/activities', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                type: activityType,
                description: description
            })
        });

        const data = await response.json();

        if (data.success) {
            descriptionInput.value = '';
            await loadActivities();
            showNotification('Activity added', 'success');
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        console.error('Error adding activity:', error);
        showNotification('Error adding activity', 'error');
    }
}

// ===== UTILITIES =====

function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 3000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
