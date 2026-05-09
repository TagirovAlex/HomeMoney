// =========================================
// main.js - Основной скрипт клиентской логики
// =========================================

/**
 * 1. Логика переключения темы (Dark/Light Mode)
 */
document.addEventListener('DOMContentLoaded', () => {
    const toggleButton = document.getElementById('theme-toggle');
    const htmlElement = document.documentElement;
    
    function initializeTheme() {
        // Поиск в localStorage, затем проверка системных настроек ОС
        let storedTheme = localStorage.getItem('theme');
        if (storedTheme) {
            htmlElement.setAttribute('data-theme', storedTheme);
            updateToggleIcon(storedTheme);
        } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            // Автоматическое определение темы по ОС
            localStorage.setItem('theme', 'dark');
            htmlElement.setAttribute('data-theme', 'dark');
            updateToggleIcon('dark');
        } else {
             // По умолчанию - светлая тема
            htmlElement.setAttribute('data-theme', 'light');
            updateToggleIcon('light');
        }
    }

    function updateToggleIcon(theme) {
        toggleButton.textContent = theme === 'dark' ? '☀️' : '🌙';
    }

    function toggleTheme() {
        let currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        let newTheme = currentTheme === 'light' ? 'dark' : 'light';
        
        htmlElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateToggleIcon(newTheme);
    }

    toggleButton.addEventListener('click', toggleTheme);
    initializeTheme();
});


/**
 * 2. Логика загрузки данных с API (Dashboard)
 */
async function loadDashboardData() {
    console.log("Attempting to load financial data from API...");
    try {
        // Запрашиваем данные сводки за текущий тестовый период (Май 2024)
        const response = await fetch('/api/v1/transactions'); 
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();

        if (data.status === 'success') {
            const summary = data.data;
            document.getElementById('total-spent').textContent = `${summary.total_spent.toFixed(2)} RUB`;
            document.getElementById('total-budgeted').textContent = `${summary.total_budgeted.toFixed(2)} RUB`;

            // В реальном приложении здесь будет вызов функции для заполнения таблицы транзакций
            console.log("Dashboard data loaded successfully.");
        } else {
            alert(`Ошибка загрузки данных: ${data.message}`);
        }
    } catch (error) {
        console.error("Критическая ошибка при загрузке данных с API:", error);
    }
}

// Загружаем данные после того, как DOM полностью готов
window.onload = loadDashboardData;