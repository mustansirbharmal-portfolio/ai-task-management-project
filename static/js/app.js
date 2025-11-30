/**
 * Smart Task Analyzer - Premium Frontend Application
 * Modern, aesthetic task management with AI-powered prioritization
 */

// API Base URL
const API_BASE = '/api';

// State Management
let currentTasks = [];
let analyzedTasks = [];
let currentFeedbackTaskId = null;

// Strategy Descriptions
const strategyDescriptions = {
    'smart_balance': '🎯 <strong>Smart Balance:</strong> Intelligently weighs urgency, importance, effort, and dependencies for optimal prioritization.',
    'fastest_wins': '⚡ <strong>Fastest Wins:</strong> Prioritizes low-effort tasks that can be completed quickly for momentum and productivity.',
    'high_impact': '🌟 <strong>High Impact:</strong> Focuses on the most important tasks regardless of effort or deadline pressure.',
    'deadline_driven': '📅 <strong>Deadline Driven:</strong> Prioritizes tasks based primarily on their due dates and urgency.'
};

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    initializeNavigation();
    initializeForm();
    initializeWeightSliders();
    initializeStrategySelector();
    setDefaultDate();
    loadInitialData();
});

/**
 * Navigation
 */
function initializeNavigation() {
    document.querySelectorAll('[data-section]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const section = e.currentTarget.dataset.section;
            showSection(section);
            
            // Update active nav
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            e.currentTarget.classList.add('active');
        });
    });
}

function showSection(sectionName) {
    document.querySelectorAll('.section-content').forEach(section => {
        section.classList.add('d-none');
    });
    document.getElementById(`${sectionName}-section`).classList.remove('d-none');
    
    // Load section-specific data
    if (sectionName === 'matrix') {
        loadMatrix();
    } else if (sectionName === 'settings') {
        loadWeights();
        loadFeedbackStats();
    }
}

/**
 * Form Handling
 */
function initializeForm() {
    // Task form submission
    document.getElementById('add-task-form').addEventListener('submit', (e) => {
        e.preventDefault();
        addTask();
    });
    
    // Importance slider
    document.getElementById('task-importance').addEventListener('input', (e) => {
        document.getElementById('importance-value').textContent = e.target.value;
    });
}

function setDefaultDate() {
    const today = new Date();
    const nextWeek = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);
    document.getElementById('task-due-date').value = nextWeek.toISOString().split('T')[0];
}

function addTask() {
    const title = document.getElementById('task-title').value.trim();
    const dueDate = document.getElementById('task-due-date').value;
    const hours = parseFloat(document.getElementById('task-hours').value);
    const importance = parseInt(document.getElementById('task-importance').value);
    const depsInput = document.getElementById('task-dependencies').value.trim();
    
    // Validation
    if (!title) {
        showToast('Please enter a task title', 'error');
        return;
    }
    
    if (!dueDate) {
        showToast('Please select a due date', 'error');
        return;
    }
    
    const task = {
        id: `task-${Date.now()}`,
        title: title,
        due_date: dueDate,
        estimated_hours: hours,
        importance: importance,
        dependencies: depsInput ? depsInput.split(',').map(d => d.trim()).filter(d => d) : []
    };
    
    currentTasks.push(task);
    
    // Clear form
    document.getElementById('task-title').value = '';
    document.getElementById('task-importance').value = 5;
    document.getElementById('importance-value').textContent = '5';
    document.getElementById('task-dependencies').value = '';
    setDefaultDate();
    
    showToast(`Task "${title}" added successfully!`, 'success');
    updateStats();
    
    // Auto-analyze if we have tasks
    if (currentTasks.length > 0) {
        analyzeTasks();
    }
}

/**
 * Bulk Import
 */
function importBulkTasks() {
    const jsonInput = document.getElementById('bulk-json').value.trim();
    
    if (!jsonInput) {
        showToast('Please paste JSON data', 'error');
        return;
    }
    
    try {
        const tasks = JSON.parse(jsonInput);
        
        if (!Array.isArray(tasks)) {
            showToast('JSON must be an array of tasks', 'error');
            return;
        }
        
        // Validate and add IDs
        tasks.forEach((task, index) => {
            if (!task.id) {
                task.id = `imported-${Date.now()}-${index}`;
            }
        });
        
        currentTasks = [...currentTasks, ...tasks];
        document.getElementById('bulk-json').value = '';
        
        showToast(`${tasks.length} tasks imported successfully!`, 'success');
        updateStats();
        analyzeTasks();
        
    } catch (e) {
        showToast('Invalid JSON format: ' + e.message, 'error');
    }
}

/**
 * Task Analysis
 */
async function analyzeTasks() {
    if (currentTasks.length === 0) {
        showToast('No tasks to analyze. Add some tasks first!', 'warning');
        return;
    }
    
    showLoading(true);
    
    const strategy = document.getElementById('sort-strategy').value;
    const considerWeekends = document.getElementById('consider-weekends')?.checked ?? true;
    
    // Get custom weights if enabled
    let weights = null;
    if (document.getElementById('enable-custom-weights')?.checked) {
        weights = {
            urgency_weight: parseInt(document.getElementById('urgency-weight').value) / 100,
            importance_weight: parseInt(document.getElementById('importance-weight').value) / 100,
            effort_weight: parseInt(document.getElementById('effort-weight').value) / 100,
            blocking_weight: parseInt(document.getElementById('blocking-weight').value) / 100,
            custom_weights_enabled: true
        };
    }
    
    try {
        const response = await fetch(`${API_BASE}/tasks/analyze/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tasks: currentTasks,
                strategy: strategy,
                weights: weights,
                consider_weekends: considerWeekends
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            analyzedTasks = data.tasks;
            renderTasks(analyzedTasks);
            updateStats();
            refreshSuggestions();
            
            // Show circular dependency warning
            if (data.has_circular_dependencies) {
                showToast(`Warning: Circular dependencies detected in tasks: ${data.circular_dependency_tasks.join(', ')}`, 'warning');
            }
            
            showToast(`${data.total_tasks} tasks analyzed successfully!`, 'success');
        } else {
            showToast(data.error || 'Analysis failed', 'error');
        }
        
    } catch (e) {
        showToast('Failed to analyze tasks: ' + e.message, 'error');
    } finally {
        showLoading(false);
    }
}

function renderTasks(tasks) {
    const container = document.getElementById('tasks-container');
    document.getElementById('tasks-count').textContent = `${tasks.length} tasks`;
    
    if (tasks.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">
                    <i class="bi bi-clipboard-data"></i>
                </div>
                <div class="empty-state-title">No tasks analyzed</div>
                <div class="empty-state-text">Add tasks from the Dashboard and click "Analyze" to see prioritized results</div>
            </div>
        `;
        return;
    }
    
    container.innerHTML = tasks.map((task, index) => `
        <div class="task-card priority-${task.priority_level.toLowerCase()} ${task.is_overdue ? 'overdue' : ''} fade-in" style="animation-delay: ${index * 0.05}s">
            <div class="task-header">
                <div class="task-badges">
                    <span class="priority-badge ${task.priority_level.toLowerCase()}">${task.priority_level}</span>
                    ${task.is_overdue ? '<span class="badge bg-danger">OVERDUE</span>' : ''}
                    ${task.in_dependency_cycle ? '<span class="badge bg-warning">Cycle</span>' : ''}
                </div>
                <div class="task-score-total">
                    <div class="score-value">${(task.priority_score * 100).toFixed(0)}</div>
                    <div class="score-label">Score</div>
                </div>
            </div>
            
            <div class="task-title">${escapeHtml(task.title)}</div>
            
            <div class="task-meta">
                <span><i class="bi bi-calendar3"></i>${task.due_date} (${task.days_until_due >= 0 ? task.days_until_due + ' days' : Math.abs(task.days_until_due) + ' days overdue'})</span>
                <span><i class="bi bi-hourglass-split"></i>${task.estimated_hours}h</span>
                <span><i class="bi bi-star-fill"></i>${task.importance}/10</span>
            </div>
            
            ${task.dependencies.length > 0 ? `
                <div class="mb-3">
                    ${task.dependencies.map(d => `<span class="dependency-tag"><i class="bi bi-link-45deg me-1"></i>${escapeHtml(d)}</span>`).join('')}
                </div>
            ` : ''}
            
            <div class="task-explanation">${task.score_explanation}</div>
            
            <div class="task-scores">
                <div class="score-item">
                    <div class="score-item-label">Urgency</div>
                    <div class="score-item-value">${(task.urgency_score * 100).toFixed(0)}%</div>
                    <div class="score-bar"><div class="score-bar-fill urgency" style="width: ${Math.min(task.urgency_score * 100, 100)}%"></div></div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">Importance</div>
                    <div class="score-item-value">${(task.importance_score * 100).toFixed(0)}%</div>
                    <div class="score-bar"><div class="score-bar-fill importance" style="width: ${task.importance_score * 100}%"></div></div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">Effort</div>
                    <div class="score-item-value">${(task.effort_score * 100).toFixed(0)}%</div>
                    <div class="score-bar"><div class="score-bar-fill effort" style="width: ${task.effort_score * 100}%"></div></div>
                </div>
                <div class="score-item">
                    <div class="score-item-label">Blocking</div>
                    <div class="score-item-value">${(task.blocking_score * 100).toFixed(0)}%</div>
                    <div class="score-bar"><div class="score-bar-fill blocking" style="width: ${task.blocking_score * 100}%"></div></div>
                </div>
            </div>
        </div>
    `).join('');
}

/**
 * Suggestions
 */
async function refreshSuggestions() {
    const container = document.getElementById('suggestions-container');
    
    if (analyzedTasks.length === 0) {
        container.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1;">
                <div class="empty-state-icon">
                    <i class="bi bi-inbox"></i>
                </div>
                <div class="empty-state-title">No suggestions yet</div>
                <div class="empty-state-text">Add tasks below to get AI-powered prioritization suggestions</div>
            </div>
        `;
        return;
    }
    
    // Get top 3 suggestions
    const suggestions = analyzedTasks.slice(0, 3);
    
    container.innerHTML = suggestions.map((task, index) => `
        <div class="suggestion-card fade-in" style="animation-delay: ${index * 0.1}s">
            <div class="suggestion-header">
                <div class="suggestion-rank">${index + 1}</div>
                <span class="priority-badge ${task.priority_level.toLowerCase()}">${task.priority_level}</span>
            </div>
            <div class="suggestion-title">${escapeHtml(task.title)}</div>
            <div class="suggestion-meta">
                <span><i class="bi bi-calendar3"></i>${task.due_date} ${task.is_overdue ? '(Overdue!)' : `(${task.days_until_due} days)`}</span>
                <span><i class="bi bi-hourglass-split"></i>${task.estimated_hours} hours estimated</span>
                <span><i class="bi bi-star-fill"></i>Importance: ${task.importance}/10</span>
            </div>
            <div class="suggestion-footer">
                <div>
                    <span class="suggestion-score">${(task.priority_score * 100).toFixed(0)}</span>
                    <span class="suggestion-score-label">Priority Score</span>
                </div>
                <button class="btn btn-sm btn-outline-light" onclick="openFeedbackModal('${task.id}', '${escapeHtml(task.title).replace(/'/g, "\\'")}')">
                    <i class="bi bi-chat-heart"></i>
                </button>
            </div>
        </div>
    `).join('');
}

/**
 * Eisenhower Matrix
 */
async function loadMatrix() {
    if (analyzedTasks.length === 0 && currentTasks.length > 0) {
        await analyzeTasks();
    }
    
    if (analyzedTasks.length === 0) {
        ['do-now', 'schedule', 'delegate', 'drop'].forEach(quadrant => {
            document.getElementById(`matrix-${quadrant}`).innerHTML = '<p class="text-center">No tasks</p>';
        });
        return;
    }
    
    // Categorize tasks
    const matrix = {
        'do_now': [],
        'schedule': [],
        'delegate': [],
        'drop': []
    };
    
    analyzedTasks.forEach(task => {
        const isUrgent = task.urgency_score >= 0.6 || task.is_overdue;
        const isImportant = task.importance_score >= 0.6;
        
        if (isUrgent && isImportant) {
            matrix.do_now.push(task);
        } else if (!isUrgent && isImportant) {
            matrix.schedule.push(task);
        } else if (isUrgent && !isImportant) {
            matrix.delegate.push(task);
        } else {
            matrix.drop.push(task);
        }
    });
    
    // Render each quadrant
    renderMatrixQuadrant('do-now', matrix.do_now);
    renderMatrixQuadrant('schedule', matrix.schedule);
    renderMatrixQuadrant('delegate', matrix.delegate);
    renderMatrixQuadrant('drop', matrix.drop);
}

function renderMatrixQuadrant(quadrantId, tasks) {
    const container = document.getElementById(`matrix-${quadrantId}`);
    
    if (tasks.length === 0) {
        container.innerHTML = `
            <div class="matrix-empty">
                <i class="bi bi-inbox d-block"></i>
                <p>No tasks in this quadrant</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = tasks.map(task => `
        <div class="matrix-task">
            <div class="d-flex justify-content-between align-items-start">
                <div class="flex-grow-1">
                    <div class="matrix-task-title">${escapeHtml(task.title)}</div>
                    <div class="matrix-task-meta">${task.due_date} • ${task.estimated_hours}h • Importance: ${task.importance}/10</div>
                </div>
                <span class="matrix-task-score">${(task.priority_score * 100).toFixed(0)}</span>
            </div>
        </div>
    `).join('');
}

/**
 * Weight Configuration
 */
function initializeWeightSliders() {
    const sliders = ['urgency', 'importance', 'effort', 'blocking'];
    
    sliders.forEach(name => {
        const slider = document.getElementById(`${name}-weight`);
        slider.addEventListener('input', () => {
            updateWeightDisplay(name);
            updateTotalWeight();
        });
    });
    
    // Enable/disable toggle
    document.getElementById('enable-custom-weights').addEventListener('change', (e) => {
        const enabled = e.target.checked;
        sliders.forEach(name => {
            document.getElementById(`${name}-weight`).disabled = !enabled;
        });
        document.getElementById('save-weights-btn').disabled = !enabled;
    });
}

function updateWeightDisplay(name) {
    const value = document.getElementById(`${name}-weight`).value;
    document.getElementById(`${name}-weight-value`).textContent = `${value}%`;
}

function updateTotalWeight() {
    const total = ['urgency', 'importance', 'effort', 'blocking']
        .reduce((sum, name) => sum + parseInt(document.getElementById(`${name}-weight`).value), 0);
    
    const totalEl = document.getElementById('total-weight');
    const alertEl = document.getElementById('weights-total');
    
    totalEl.textContent = `${total}%`;
    
    if (total === 100) {
        alertEl.classList.remove('alert-danger');
        alertEl.classList.add('alert-secondary');
    } else {
        alertEl.classList.remove('alert-secondary');
        alertEl.classList.add('alert-danger');
    }
}

async function loadWeights() {
    try {
        const response = await fetch(`${API_BASE}/tasks/weights/`);
        const data = await response.json();
        
        if (data.success && data.weights) {
            const weights = data.weights;
            document.getElementById('urgency-weight').value = Math.round(weights.urgency_weight * 100);
            document.getElementById('importance-weight').value = Math.round(weights.importance_weight * 100);
            document.getElementById('effort-weight').value = Math.round(weights.effort_weight * 100);
            document.getElementById('blocking-weight').value = Math.round(weights.blocking_weight * 100);
            
            ['urgency', 'importance', 'effort', 'blocking'].forEach(updateWeightDisplay);
            updateTotalWeight();
            
            if (weights.custom_weights_enabled) {
                document.getElementById('enable-custom-weights').checked = true;
                document.getElementById('enable-custom-weights').dispatchEvent(new Event('change'));
            }
        }
    } catch (e) {
        console.error('Failed to load weights:', e);
    }
}

async function saveWeights() {
    const total = ['urgency', 'importance', 'effort', 'blocking']
        .reduce((sum, name) => sum + parseInt(document.getElementById(`${name}-weight`).value), 0);
    
    if (total !== 100) {
        showToast('Weights must sum to 100%', 'error');
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await fetch(`${API_BASE}/tasks/weights/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                weights: {
                    urgency_weight: parseInt(document.getElementById('urgency-weight').value) / 100,
                    importance_weight: parseInt(document.getElementById('importance-weight').value) / 100,
                    effort_weight: parseInt(document.getElementById('effort-weight').value) / 100,
                    blocking_weight: parseInt(document.getElementById('blocking-weight').value) / 100,
                    custom_weights_enabled: true
                }
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Weights saved successfully!', 'success');
        } else {
            showToast(data.error || 'Failed to save weights', 'error');
        }
    } catch (e) {
        showToast('Failed to save weights: ' + e.message, 'error');
    } finally {
        showLoading(false);
    }
}

/**
 * Strategy Selector
 */
function initializeStrategySelector() {
    document.getElementById('sort-strategy').addEventListener('change', (e) => {
        document.getElementById('strategy-description').innerHTML = strategyDescriptions[e.target.value];
    });
}

/**
 * Feedback System
 */
function openFeedbackModal(taskId, taskTitle) {
    currentFeedbackTaskId = taskId;
    document.getElementById('feedback-task-title').textContent = `Task: "${taskTitle}"`;
    document.getElementById('feedback-text').value = '';
    
    const modal = new bootstrap.Modal(document.getElementById('feedbackModal'));
    modal.show();
}

async function submitFeedback(helpful) {
    if (!currentFeedbackTaskId) return;
    
    try {
        const response = await fetch(`${API_BASE}/tasks/feedback/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task_id: currentFeedbackTaskId,
                helpful: helpful,
                feedback_text: document.getElementById('feedback-text').value
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Thank you for your feedback!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('feedbackModal')).hide();
            loadFeedbackStats();
        } else {
            showToast(data.error || 'Failed to submit feedback', 'error');
        }
    } catch (e) {
        showToast('Failed to submit feedback: ' + e.message, 'error');
    }
    
    currentFeedbackTaskId = null;
}

async function loadFeedbackStats() {
    // This would typically call an API endpoint
    // For now, we'll just update the UI if we have local data
}

/**
 * Learning System
 */
async function triggerLearning() {
    showLoading(true);
    
    try {
        const response = await fetch(`${API_BASE}/tasks/learn/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('learning-result').classList.remove('d-none');
            document.getElementById('learning-reasoning').textContent = data.reasoning || 'Weights optimized based on your feedback patterns.';
            
            // Update weight sliders
            if (data.new_weights) {
                document.getElementById('urgency-weight').value = Math.round(data.new_weights.urgency_weight * 100);
                document.getElementById('importance-weight').value = Math.round(data.new_weights.importance_weight * 100);
                document.getElementById('effort-weight').value = Math.round(data.new_weights.effort_weight * 100);
                document.getElementById('blocking-weight').value = Math.round(data.new_weights.blocking_weight * 100);
                
                ['urgency', 'importance', 'effort', 'blocking'].forEach(updateWeightDisplay);
                updateTotalWeight();
            }
            
            // Update feedback counts
            if (data.feedback_summary) {
                document.getElementById('helpful-count').textContent = data.feedback_summary.helpful;
                document.getElementById('not-helpful-count').textContent = data.feedback_summary.not_helpful;
            }
            
            showToast('Weights optimized with AI!', 'success');
        } else {
            showToast(data.message || data.error || 'Learning failed', 'warning');
        }
    } catch (e) {
        showToast('Failed to trigger learning: ' + e.message, 'error');
    } finally {
        showLoading(false);
    }
}

/**
 * Statistics
 */
function updateStats() {
    const tasks = analyzedTasks.length > 0 ? analyzedTasks : currentTasks;
    
    document.getElementById('stat-total').textContent = tasks.length;
    
    if (analyzedTasks.length > 0) {
        document.getElementById('stat-overdue').textContent = analyzedTasks.filter(t => t.is_overdue).length;
        document.getElementById('stat-urgent').textContent = analyzedTasks.filter(t => t.days_until_due >= 0 && t.days_until_due <= 3).length;
        document.getElementById('stat-quickwins').textContent = analyzedTasks.filter(t => t.effort_score >= 0.7).length;
    }
}

/**
 * Load Initial Data
 */
async function loadInitialData() {
    try {
        const response = await fetch(`${API_BASE}/tasks/`);
        const data = await response.json();
        
        if (data.success && data.tasks && data.tasks.length > 0) {
            // Load existing tasks
            currentTasks = data.tasks;
            analyzedTasks = data.tasks;
            renderTasks(analyzedTasks);
            updateStats();
            refreshSuggestions();
        }
    } catch (e) {
        console.log('No existing tasks found');
    }
}

/**
 * Utility Functions
 */
function showLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    if (show) {
        overlay.classList.remove('d-none');
    } else {
        overlay.classList.add('d-none');
    }
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('notification-toast');
    const toastBody = document.getElementById('toast-message');
    
    // Set message
    toastBody.textContent = message;
    
    // Set color based on type
    toast.className = 'toast';
    switch (type) {
        case 'success':
            toast.classList.add('border-success');
            break;
        case 'error':
            toast.classList.add('border-danger');
            break;
        case 'warning':
            toast.classList.add('border-warning');
            break;
        default:
            toast.classList.add('border-secondary');
    }
    
    // Show toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
