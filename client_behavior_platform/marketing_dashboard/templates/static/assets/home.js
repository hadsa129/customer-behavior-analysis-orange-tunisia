document.addEventListener('DOMContentLoaded', function() {
    // Data passed from backend (replace with actual data)
    var cheques_by_month = [
        { date__month: "January", count: 10 },
        { date__month: "February", count: 15 },
        // Add other months
    ];

    var employees_by_type = [
        { user_type: "Full-Time", count: 30 },
        { user_type: "Part-Time", count: 20 },
        // Add other employee types
    ];

    var balances_by_region = [
        { region: "North", total_balance: 5000 },
        { region: "South", total_balance: 3000 },
        // Add other regions
    ];

    // Graphique des Chèques par Mois
    var ctx1 = document.getElementById('chequesByMonthChart').getContext('2d');
    var chequesByMonthChart = new Chart(ctx1, {
        type: 'bar',
        data: {
            labels: cheques_by_month.map(entry => `Month ${entry.date__month}`),
            datasets: [{
                label: 'Number of Cheques by Month',
                data: cheques_by_month.map(entry => entry.count),
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1
            }]
        },
        options: {
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });

    // Graphique des Employés par Type
    var ctx2 = document.getElementById('employeesByTypeChart').getContext('2d');
    var employeesByTypeChart = new Chart(ctx2, {
        type: 'pie',
        data: {
            labels: employees_by_type.map(entry => entry.user_type),
            datasets: [{
                label: 'Employee Distribution by Type',
                data: employees_by_type.map(entry => entry.count),
                backgroundColor: [
                    'rgba(255, 99, 132, 0.2)',
                    'rgba(54, 162, 235, 0.2)',
                    'rgba(255, 206, 86, 0.2)'
                ],
                borderColor: [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)'
                ],
                borderWidth: 1
            }]
        }
    });

    // Graphique des Soldes par Région
    var ctx3 = document.getElementById('balancesByRegionChart').getContext('2d');
    var balancesByRegionChart = new Chart(ctx3, {
        type: 'doughnut',
        data: {
            labels: balances_by_region.map(entry => entry.region),
            datasets: [{
                label: 'Total Balance by Region',
                data: balances_by_region.map(entry => entry.total_balance),
                backgroundColor: [
                    'rgba(153, 102, 255, 0.2)',
                    'rgba(255, 159, 64, 0.2)',
                    'rgba(255, 99, 132, 0.2)'
                ],
                borderColor: [
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 159, 64, 1)',
                    'rgba(255, 99, 132, 1)'
                ],
                borderWidth: 1
            }]
        }
    });
});