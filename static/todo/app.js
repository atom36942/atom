// Atom Todo - Core App Logic (Refined Workflow)
(function() {
    'use strict';

    // --- State Management ---
    let todos = [];
    let currentEditId = null;

    const STAGES = {
        TODO: 'todo',
        IN_PROGRESS: 'in_progress',
        DONE: 'done'
    };

    // --- Selectors ---
    const todoInput = document.getElementById('todoInput');
    const addTodoBtn = document.getElementById('addTodoBtn');
    const todoList = document.getElementById('todoList');
    const inProgressList = document.getElementById('inProgressList');
    const doneList = document.getElementById('doneList');
    const todoCount = document.getElementById('todoCount');
    const inProgressCount = document.getElementById('inProgressCount');
    const doneCount = document.getElementById('doneCount');
    
    // Modal Selectors
    const editModal = document.getElementById('editModal');
    const editDesc = document.getElementById('editDesc');
    const editLink = document.getElementById('editLink');
    const editDate = document.getElementById('editDate');
    const saveEditBtn = document.getElementById('saveEditBtn');
    const cancelEditBtn = document.getElementById('cancelEditBtn');
    const deleteTaskBtn = document.getElementById('deleteTaskBtn');

    // Action Selectors
    const exportBtn = document.getElementById('exportBtn');
    const importBtn = document.getElementById('importBtn');
    const importInput = document.getElementById('importInput');

    // --- Initialization ---
    function init() {
        loadData();
        render();
        setupEventListeners();
    }

    function setupEventListeners() {
        addTodoBtn.addEventListener('click', addNewTodo);
        todoInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') addNewTodo();
        });

        saveEditBtn.addEventListener('click', saveEdit);
        cancelEditBtn.addEventListener('click', closeModal);
        deleteTaskBtn.addEventListener('click', deleteCurrentTask);

        exportBtn.addEventListener('click', exportTasks);
        importBtn.addEventListener('click', () => importInput.click());
        importInput.addEventListener('change', importTasks);

        // Drag & Drop Listeners
        [todoList, inProgressList, doneList].forEach(list => {
            list.addEventListener('dragover', (e) => {
                e.preventDefault();
                list.classList.add('over');
            });
            list.addEventListener('dragleave', () => list.classList.remove('over'));
            list.addEventListener('drop', handleDrop);
        });

        // Close modal on click outside
        window.addEventListener('click', (e) => {
            if (e.target === editModal) closeModal();
        });
    }

    // --- Logic ---

    function loadData() {
        const stored = localStorage.getItem('atom_todo_v2');
        if (stored) {
            try { todos = JSON.parse(stored); } catch (e) { todos = []; }
        }
    }

    function saveData() {
        localStorage.setItem('atom_todo_v2', JSON.stringify(todos));
        render();
    }

    function addNewTodo() {
        const desc = todoInput.value.trim();
        if (!desc) return;

        todos.unshift({
            id: `TASK-${Date.now().toString().slice(-4)}`,
            description: desc,
            link: '',
            dueDate: '',
            stage: STAGES.TODO,
            createdAt: Date.now()
        });

        todoInput.value = '';
        saveData();
    }

    function openEdit(id) {
        const todo = todos.find(t => t.id === id);
        if (!todo) return;

        currentEditId = id;
        editDesc.value = todo.description;
        editLink.value = todo.link || '';
        editDate.value = todo.dueDate || '';

        // Ensure the date picker opens on click of the field
        editDate.onclick = () => {
            if (typeof editDate.showPicker === 'function') {
                editDate.showPicker();
            }
        };

        editModal.style.display = 'flex';
    }

    function saveEdit() {
        const todo = todos.find(t => t.id === currentEditId);
        if (todo) {
            todo.description = editDesc.value.trim();
            todo.link = editLink.value.trim();
            todo.dueDate = editDate.value;
            saveData();
        }
        closeModal();
    }

    function deleteCurrentTask() {
        todos = todos.filter(t => t.id !== currentEditId);
        saveData();
        closeModal();
    }

    function closeModal() {
        editModal.style.display = 'none';
        currentEditId = null;
    }

    function handleDrop(e) {
        e.preventDefault();
        e.currentTarget.classList.remove('over');
        const id = e.dataTransfer.getData('text/plain');
        const newStage = e.currentTarget.parentNode.dataset.stage;
        
        const todo = todos.find(t => t.id === id);
        if (todo && todo.stage !== newStage) {
            todo.stage = newStage;
            saveData();
        }
    }

    // --- UI Rendering ---

    function render() {
        [todoList, inProgressList, doneList].forEach(l => l.innerHTML = '');
        let counts = { [STAGES.TODO]: 0, [STAGES.IN_PROGRESS]: 0, [STAGES.DONE]: 0 };

        todos.forEach(todo => {
            const el = createTaskElement(todo);
            const list = getListByStage(todo.stage);
            if (list) {
                list.appendChild(el);
                counts[todo.stage]++;
            }
        });

        todoCount.textContent = counts[STAGES.TODO];
        inProgressCount.textContent = counts[STAGES.IN_PROGRESS];
        doneCount.textContent = counts[STAGES.DONE];
    }

    function getListByStage(stage) {
        if (stage === STAGES.TODO) return todoList;
        if (stage === STAGES.IN_PROGRESS) return inProgressList;
        if (stage === STAGES.DONE) return doneList;
        return null;
    }

    function createTaskElement(todo) {
        const div = document.createElement('div');
        div.className = 'task-item';
        div.draggable = true;
        div.dataset.id = todo.id;
        div.onclick = () => openEdit(todo.id);
        
        div.addEventListener('dragstart', (e) => {
            e.dataTransfer.setData('text/plain', todo.id);
            div.classList.add('dragging');
        });
        div.addEventListener('dragend', () => div.classList.remove('dragging'));

        let linkDisplay = '';
        if (todo.link) {
            try {
                const cleanLink = todo.link.startsWith('http') ? todo.link : `https://${todo.link}`;
                const hostname = new URL(cleanLink).hostname;
                linkDisplay = `<a href="${cleanLink}" class="task-link" target="_blank" onclick="event.stopPropagation()">🔗 ${hostname}</a>`;
            } catch (e) {
                linkDisplay = `<span class="task-link">🔗 Invalid Link</span>`;
            }
        }

        div.innerHTML = `
            <div class="task-text">${escapeHtml(todo.description)}</div>
            <div class="task-meta">
                ${todo.dueDate ? `<span>📅 ${todo.dueDate}</span>` : ''}
                ${linkDisplay}
            </div>
        `;

        return div;
    }

    // --- Utils ---

    function exportTasks() {
        const blob = new Blob([JSON.stringify(todos, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `atom_tasks_${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }

    function importTasks(e) {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (event) => {
            try {
                const imported = JSON.parse(event.target.result);
                if (Array.isArray(imported)) {
                    todos = imported;
                    saveData();
                }
            } catch (err) { alert("Invalid JSON"); }
        };
        reader.readAsText(file);
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    init();
})();
