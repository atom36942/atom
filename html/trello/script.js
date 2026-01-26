document.addEventListener('DOMContentLoaded', () => {
    // --- State Management ---
    let tasks = [];
    const TODO_COLUMN_ID = 'todo-list';
    const IN_PROGRESS_COLUMN_ID = 'inprogress-list';
    const DONE_COLUMN_ID = 'done-list';

    // --- DOM Elements ---
    const todoList = document.getElementById(TODO_COLUMN_ID);
    const inProgressList = document.getElementById(IN_PROGRESS_COLUMN_ID);
    const doneList = document.getElementById(DONE_COLUMN_ID);
    const addTaskBtn = document.getElementById('add-task-btn');
    const taskModal = document.getElementById('task-modal');
    const closeModal = document.querySelector('.close-modal');
    const cancelBtn = document.querySelector('.cancel-btn');
    const taskForm = document.getElementById('task-form');
    const modalTitle = document.getElementById('modal-title');
    const taskIdInput = document.getElementById('task-id');
    const taskTitleInput = document.getElementById('task-title');
    const taskDescInput = document.getElementById('task-desc');
    const taskStatusInput = document.getElementById('task-status');

    // --- Initialization ---
    loadTasks();
    renderTasks();

    // --- Event Listeners ---
    addTaskBtn.addEventListener('click', () => {
        openModal();
    });

    closeModal.addEventListener('click', closeModalFunc);
    cancelBtn.addEventListener('click', closeModalFunc);

    window.addEventListener('click', (e) => {
        if (e.target === taskModal) {
            closeModalFunc();
        }
    });

    taskForm.addEventListener('submit', (e) => {
        e.preventDefault();
        saveTask();
    });

    // --- Functions ---

    function loadTasks() {
        const storedTasks = localStorage.getItem('kanban-tasks');
        if (storedTasks) {
            tasks = JSON.parse(storedTasks);
        } else {
            // Default tasks for demonstration
            tasks = [
                { id: '1', title: 'Welcome to Kanban', description: 'This is a sample task. Try dragging it!', status: 'todo' },
                { id: '2', title: 'In Progress Task', description: 'This task is currently being worked on.', status: 'inprogress' },
                { id: '3', title: 'Completed Task', description: 'This task is already done.', status: 'done' }
            ];
            saveTasksToLocalStorage();
        }
    }

    function saveTasksToLocalStorage() {
        localStorage.setItem('kanban-tasks', JSON.stringify(tasks));
        updateTaskCounts();
    }

    function renderTasks() {
        // Clear existing tasks
        todoList.innerHTML = '';
        inProgressList.innerHTML = '';
        doneList.innerHTML = '';

        tasks.forEach(task => {
            const taskElement = createTaskElement(task);
            if (task.status === 'todo') {
                todoList.appendChild(taskElement);
            } else if (task.status === 'inprogress') {
                inProgressList.appendChild(taskElement);
            } else if (task.status === 'done') {
                doneList.appendChild(taskElement);
            }
        });

        updateTaskCounts();
    }

    function createTaskElement(task) {
        const div = document.createElement('div');
        div.classList.add('task-card');
        div.setAttribute('draggable', 'true');
        div.dataset.id = task.id;

        div.innerHTML = `
            <div class="task-title">${escapeHtml(task.title)}</div>
            <div class="task-desc">${escapeHtml(task.description)}</div>
            <div class="task-actions">
                <button class="edit-btn" title="Edit">&#9998;</button>
                <button class="delete-btn" title="Delete">&times;</button>
            </div>
        `;

        // Drag events
        div.addEventListener('dragstart', handleDragStart);
        div.addEventListener('dragend', handleDragEnd);

        // Click events for edit/delete
        const editBtn = div.querySelector('.edit-btn');
        const deleteBtn = div.querySelector('.delete-btn');

        editBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            openModal(task);
        });

        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteTask(task.id);
        });

        return div;
    }

    function updateTaskCounts() {
        const todoCount = tasks.filter(t => t.status === 'todo').length;
        const inProgressCount = tasks.filter(t => t.status === 'inprogress').length;
        const doneCount = tasks.filter(t => t.status === 'done').length;

        document.querySelector('#todo-column .task-count').textContent = todoCount;
        document.querySelector('#inprogress-column .task-count').textContent = inProgressCount;
        document.querySelector('#done-column .task-count').textContent = doneCount;
    }

    function openModal(task = null) {
        taskModal.classList.remove('hidden');
        if (task) {
            modalTitle.textContent = 'Edit Task';
            taskIdInput.value = task.id;
            taskTitleInput.value = task.title;
            taskDescInput.value = task.description;
            taskStatusInput.value = task.status;
        } else {
            modalTitle.textContent = 'Add New Task';
            taskForm.reset();
            taskIdInput.value = '';
            taskStatusInput.value = 'todo'; // Default status
        }
    }

    function closeModalFunc() {
        taskModal.classList.add('hidden');
    }

    function saveTask() {
        const id = taskIdInput.value;
        const title = taskTitleInput.value;
        const description = taskDescInput.value;
        const status = taskStatusInput.value;

        if (id) {
            // Edit existing task
            const index = tasks.findIndex(t => t.id === id);
            if (index !== -1) {
                tasks[index] = { ...tasks[index], title, description, status };
            }
        } else {
            // Add new task
            const newTask = {
                id: Date.now().toString(),
                title,
                description,
                status
            };
            tasks.push(newTask);
        }

        saveTasksToLocalStorage();
        renderTasks();
        closeModalFunc();
    }

    function deleteTask(id) {
        if (confirm('Are you sure you want to delete this task?')) {
            tasks = tasks.filter(t => t.id !== id);
            saveTasksToLocalStorage();
            renderTasks();
        }
    }

    function escapeHtml(text) {
        if (!text) return '';
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // --- Drag and Drop Logic ---
    let draggedItem = null;

    function handleDragStart(e) {
        draggedItem = this;
        setTimeout(() => {
            this.classList.add('dragging');
        }, 0);
    }

    function handleDragEnd(e) {
        this.classList.remove('dragging');
        draggedItem = null;
        
        // Remove visuals
        document.querySelectorAll('.task-list').forEach(list => {
            list.classList.remove('drag-over');
        });
    }

    const columns = document.querySelectorAll('.task-list');

    columns.forEach(column => {
        column.addEventListener('dragover', (e) => {
            e.preventDefault();
            column.classList.add('drag-over');
            
            const afterElement = getDragAfterElement(column, e.clientY);
            const draggable = document.querySelector('.dragging');
            
            if (afterElement == null) {
                column.appendChild(draggable);
            } else {
                column.insertBefore(draggable, afterElement);
            }
        });

        column.addEventListener('dragleave', () => {
            column.classList.remove('drag-over');
        });

        column.addEventListener('drop', (e) => {
            column.classList.remove('drag-over');
            const draggable = document.querySelector('.dragging');
            
            // Determine new status based on column ID
            let newStatus;
            if (column.id === TODO_COLUMN_ID) newStatus = 'todo';
            else if (column.id === IN_PROGRESS_COLUMN_ID) newStatus = 'inprogress';
            else if (column.id === DONE_COLUMN_ID) newStatus = 'done';

            // Update task status in state
            const taskId = draggable.dataset.id;
            const taskIndex = tasks.findIndex(t => t.id === taskId);
            
            if (taskIndex !== -1 && tasks[taskIndex].status !== newStatus) {
                tasks[taskIndex].status = newStatus;
                saveTasksToLocalStorage();
                updateTaskCounts(); // Update counts since task moved
            }
        });
    });

    function getDragAfterElement(container, y) {
        const draggableElements = [...container.querySelectorAll('.task-card:not(.dragging)')];

        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;
            
            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    }
});
