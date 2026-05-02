// Configuration des graphiques
function initGauge(elementId, value, max, color) {
    const element = document.getElementById(elementId);
    if (!element) {
        console.error(`Élément avec l'ID ${elementId} non trouvé`);
        return null;
    }
    
    const ctx = element.getContext('2d');
    if (!ctx) {
        console.error('Impossible d\'obtenir le contexte 2D');
        return null;
    }
    
    const gradient = ctx.createLinearGradient(0, 0, 300, 0);
    
    // Configuration du dégradé en fonction de la couleur
    if (color === 'green') {
        gradient.addColorStop(0, '#10B981');
        gradient.addColorStop(1, '#059669');
    } else if (color === 'blue') {
        gradient.addColorStop(0, '#3B82F6');
        gradient.addColorStop(1, '#2563EB');
    } else if (color === 'red') {
        gradient.addColorStop(0, '#EF4444');
        gradient.addColorStop(1, '#DC2626');
    } else if (color === 'yellow') {
        gradient.addColorStop(0, '#F59E0B');
        gradient.addColorStop(1, '#D97706');
    } else if (color === 'purple') {
        gradient.addColorStop(0, '#8B5CF6');
        gradient.addColorStop(1, '#7C3AED');
    } else {
        // Couleur par défaut si aucune correspondance
        gradient.addColorStop(0, '#3B82F6');
        gradient.addColorStop(1, '#1D4ED8');
    }
    
    // Vérification des valeurs numériques
    const numericValue = Number(value) || 0;
    const numericMax = Number(max) || 100;
    
    try {
        return new Chart(ctx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [numericValue, Math.max(0, numericMax - numericValue)],
                    backgroundColor: [gradient, '#E5E7EB'],
                    borderWidth: 0,
                    circumference: 180,
                    rotation: 270,
                    cutout: '80%',
                    borderRadius: 20
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '80%',
                rotation: Math.PI,
                circumference: 180,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                }
            }
        });
    } catch (error) {
        console.error('Erreur lors de l\'initialisation de la jauge:', error);
        return null;
    }
}
// Initialisation des graphiques au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    try {
        // Vérifier que les éléments existent avant de les utiliser
        const engagementGauge = document.getElementById('engagementGauge');
        const rentabilityGauge = document.getElementById('rentabilityGauge');
        const consumptionChart = document.getElementById('consumptionChart');
        
        // Jauge d'engagement
        if (engagementGauge) {
            const engagementScore = 0; // Valeur par défaut, à remplacer par la valeur dynamique
            initGauge('engagementGauge', engagementScore, 500, 'purple');
        }
        
        // Jauge de rentabilité
        if (rentabilityGauge) {
            const rentabilityClass = ''; // Valeur par défaut, à remplacer par la valeur dynamique
            let rentabilityScore = 30; // Valeur par défaut pour 'low'
            
            if (rentabilityClass === 'high') {
                rentabilityScore = 90;
            } else if (rentabilityClass === 'medium') {
                rentabilityScore = 60;
            }
            
            initGauge('rentabilityGauge', rentabilityScore, 100, 'green');
        }
        
        // Graphique de consommation
        if (consumptionChart) {
            const consumptionCtx = consumptionChart.getContext('2d');
            if (consumptionCtx) {
                const consumptionData = {
                    labels: ['Données (Mo)', 'Appels (min)', 'SMS'],
                    datasets: [{
                        label: 'Consommation',
                        data: [
                            0, // données_consommees
                            0, // voix_utilisee
                            0  // sms
                        ],
                        backgroundColor: [
                            'rgba(59, 130, 246, 0.7)',
                            'rgba(16, 185, 129, 0.7)',
                            'rgba(139, 92, 246, 0.7)'
                        ],
                        borderColor: [
                            'rgba(59, 130, 246, 1)',
                            'rgba(16, 185, 129, 1)',
                            'rgba(139, 92, 246, 1)'
                        ],
                        borderWidth: 1
                    }]
                };
                
                const consumptionOptions = {
                    responsive: true,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    let label = context.dataset.label || '';
                                    if (label) {
                                        label += ': ';
                                    }
                                    if (context.parsed !== null) {
                                        label += context.parsed + ' ';
                                        if (context.label.includes('Données')) {
                                            label += 'Mo';
                                        } else if (context.label.includes('Appels')) {
                                            label += 'min';
                                        }
                                    }
                                    return label;
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return value + (this.getLabelForValue(0).includes('Données') ? ' Mo' : 
                                                  this.getLabelForValue(0).includes('Appels') ? ' min' : '');
                                }
                            }
                        }
                    }
                };
                
                new Chart(consumptionCtx, {
                    type: 'bar',
                    data: consumptionData,
                    options: consumptionOptions
                });
            }
        }
    } catch (error) {
        console.error('Erreur lors de l\'initialisation des graphiques :', error);
    }
});

// Gestion des modales
document.addEventListener('DOMContentLoaded', function() {
    // Fonction pour afficher une modale
    window.showModal = function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden'; // Empêche le défilement de la page
        }
    };
    
    // Fonction pour masquer une modale
    window.hideModal = function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('hidden');
            document.body.style.overflow = ''; // Rétablit le défilement de la page
        }
    };
    
    // Fermer la modale en cliquant en dehors
    const modals = document.querySelectorAll('.modal-overlay');
    modals.forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.add('hidden');
                document.body.style.overflow = '';
            }
        });
    });
    
    // Fermer la modale avec la touche Échap
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            modals.forEach(modal => {
                if (!modal.classList.contains('hidden')) {
                    modal.classList.add('hidden');
                    document.body.style.overflow = '';
                }
            });
        }
    });
});
