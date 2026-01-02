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
}

function selectType(type) {
    currentType = type;
    renderSidebar();
    renderActivities();
}

// ===== ACTIVITIES DISPLAY =====

function renderActivities() {
    const listDiv = document.getElementById('activitiesList');
    const header = document.getElementById('activitiesHeader');

    if (!listDiv) return;

    // Update header
    if (header) {
        header.textContent = currentType ? `${currentType} Activities` : 'All Activities';
    }

    // Get activities to display
    let activities = [];
    if (currentType === null) {
        // Show all activities from all types
        Object.values(allActivities).forEach(typeActivities => {
            activities = activities.concat(typeActivities);
        });
    } else {
        activities = allActivities[currentType] || [];
    }

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

function renderActivityItem(activity) {
    const isTodo = activity.type === 'todo';

    // Render checkbox for todo items (now on the right side)
    const checkboxHtml = isTodo ? `
        <div class="checkbox-wrapper">
            <input
                type="checkbox"
                ${activity.completed ? 'checked' : ''}
                onchange="toggleCompletion(${activity.id}, this.checked)"
            >
            <div class="checkbox-custom"></div>
        </div>
    ` : '';

    // Show type label only when viewing all activities
    const typeLabel = currentType === null ? `<span class="activity-type">[${activity.type}]</span>` : '';

    return `
        <li class="activity-item ${activity.completed ? 'completed' : ''}">
            <span class="activity-description">${escapeHtml(activity.description)}</span>
            ${typeLabel}
            ${checkboxHtml}
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
                <span class="activity-type">[${escapeHtml(data.activity.type)}]</span>
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
