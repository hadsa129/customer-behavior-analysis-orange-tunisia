

def get_interactive_chat_fix():
    
    def interactive_chat(self):
        """Interface interactive complète"""
        print("""
        ====================================
        Assistant Marketing - Orange Tunisie
        ====================================
        Commandes:
        - 'quit'/'exit' pour quitter
        - 'history' pour voir l'historique
        - 'stats' pour les statistiques d'usage
        """)
        
        while True:
            try:
                query = input("\nQuestion marketing: ").strip()
                
                # Commandes spéciales
                if query.lower() in ['exit', 'quit', 'q']:
                    print("Fermeture de l'application...")
                    break
                    
                if query.lower() == 'history':
                    print("\nHistorique des requêtes:")
                    for i, entry in enumerate(self.history, 1):
                        # Vérifier si l'entrée a la structure attendue
                        if isinstance(entry, dict) and 'query' in entry:
                            timestamp = entry.get('timestamp', 'N/A')
                            query_preview = entry['query'][:50] + '...' if entry['query'] else ''
                            print(f"{i}. [{timestamp}] {query_preview}")
                    continue
                    
                if query.lower() == 'stats':
                    print("\nStatistiques d'usage:")
                    total_requests = len(self.history)
                    print(f"Total requêtes: {total_requests}")
                    
                    # Compter les succès et échecs de manière sécurisée
                    success = 0
                    for entry in self.history:
                        try:
                            if isinstance(entry, dict) and 'response' in entry and \
                               isinstance(entry['response'], dict) and \
                               entry['response'].get('status') == 'success':
                                success += 1
                        except (AttributeError, KeyError):
                            continue
                            
                    print(f"Succès: {success} | Échecs: {total_requests - success}")
                    
                    # Afficher les 5 dernières requêtes
                    print("\n5 dernières requêtes:")
                    for i, entry in enumerate(self.history[-5:], 1):
                        if isinstance(entry, dict) and 'query' in entry:
                            query_preview = entry['query'][:70] + '...' if len(entry['query']) > 70 else entry['query']
                            status = entry.get('response', {}).get('status', 'inconnu')
                            print(f"  {i}. [{status.upper()}] {query_preview}")
                    continue
                
                if not query:
                    continue
                    
                # Traitement normal
                print("\nAnalyse en cours...")
                response = self.process_query(query)
                
                # Affichage des résultats
                if response['status'] == 'success':
                    print(f"\nRésultats ({response['execution_time']:.2f}s):")
                    print(response['explanation'])
                    
                    if response['results'].get('visualization'):
                        print(f"\nVisualisation générée: {response['results']['visualization']}")
                else:
                    print(f"\nErreur: {response['message']}")
                    
                print("\n" + "="*50)
                
            except KeyboardInterrupt:
                print("\nInterruption - Tapez 'exit' pour quitter")
            except Exception as e:
                print(f"\nErreur inattendue: {str(e)}")

def get_log_interaction_fix():
    
    def _log_interaction(self, query: str, response: Dict):
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'response': {
                'status': response.get('status', 'unknown')
            }
        }
        
        # Ajouter des informations supplémentaires pour les réponses réussies
        if response.get('status') == 'success' and 'results' in response:
            log_entry['response'].update({
                'data_shape': str(response['results'].get('data', {}).shape) 
                    if hasattr(response['results'].get('data', {}), 'shape') else 'N/A',
                'has_visualization': bool(response['results'].get('visualization'))
            })
        
        self.history.append(log_entry)

if __name__ == "__main__":
    print("""
    Instructions pour corriger le problème de la commande 'stats' :
    
    1. Ouvrez le fichier chatbot.ipynb dans un éditeur de texte
    2. Remplacez la méthode interactive_chat() par le code fourni ci-dessous
    3. Remplacez également la méthode _log_interaction() par le code fourni
    4. Sauvegardez le fichier
    
    === CODE POUR interactive_chat() ===
    {}
    
    === CODE POUR _log_interaction() ===
    {}
    """.format(get_interactive_chat_fix(), get_log_interaction_fix()))
