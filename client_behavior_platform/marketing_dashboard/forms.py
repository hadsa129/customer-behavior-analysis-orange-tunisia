import re
from django import forms

def get_file_type(filename):
    """
    Détermine le type de fichier (achat, recharge, consommation, etc.)
    
    Args:
        filename (str): Nom du fichier à analyser
        
    Returns:
        str: Type de fichier ('achats', 'recharges', 'consommations', 'jeux', 'autres')
        None: Si le paramètre n'est pas une chaîne ou est vide
    """
    try:
        # Vérification des paramètres d'entrée
        if not isinstance(filename, str) or not filename.strip():
            return None
            
        filename = filename.lower().strip()
        
        # Détection du type de fichier
        if 'achat' in filename:
            return 'achats'
        if 'recharge' in filename:
            return 'recharges'
        if any(term in filename for term in ['consommation', 'conso']):
            return 'consommations'
        if any(term in filename for term in ['jeu', 'spin', 'game']):
            return 'jeux'
            
        return 'autres'
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur dans get_file_type avec filename={filename}: {str(e)}", exc_info=True)
        return None

def extract_month_year(filename):
    """
    Extrait le mois et l'année du nom de fichier
    
    Args:
        filename (str): Nom du fichier à analyser
        
    Returns:
        str: Date au format 'YYYY-MM' ou None si non trouvé ou en cas d'erreur
    """
    try:
        # Vérification des paramètres d'entrée
        if not isinstance(filename, str) or not filename.strip():
            return None
            
        filename = filename.strip()
        
        # Formats supportés :
        # - YYYY_MM, YYYY-MM, YYYY.MM
        # - MM_YYYY, MM-YYYY, MM.YYYY
        patterns = [
            # Format: YYYY_MM ou YYYY-MM ou YYYY.MM
            r'(?:^|[_\-.])(\d{4})[_\- .](\d{1,2})(?![\d])',
            # Format: MM_YYYY ou MM-YYYY ou MM.YYYY
            r'(?:^|[_\-.])(\d{1,2})[_\- .](\d{4})(?![\d])'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    # Si le premier groupe a 4 chiffres, c'est l'année
                    if len(groups[0]) == 4:
                        year = int(groups[0])
                        month = int(groups[1])
                    else:  # Sinon c'est le mois
                        year = int(groups[1])
                        month = int(groups[0])
                    
                    # Validation des valeurs
                    if 1 <= month <= 12 and 2000 <= year <= 2100:
                        return f"{year:04d}-{month:02d}"
                    
        return None
        
    except (ValueError, IndexError) as ve:
        # Erreur de conversion en int ou d'indexation
        return None
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur dans extract_month_year avec filename={filename}: {str(e)}", exc_info=True)
        return None

class AnalyseClientForm(forms.Form):
    msisdn = forms.CharField(label='MSISDN (Identifiant Client)', max_length=100)
    date_debut = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    date_fin = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))


SEGMENTS_POSSIBLES = {
    'rentabilite': ['non rentable', 'rentable'],
    'engagement': ['non engagé', 'peu engagé', 'très engagé'],
    'type_client': ['orienté USSD', 'orienté APLICATION', 'orienté BOUTIQUE'],
    'type_interet': ['data', 'voix'],
    'interet_international': ['non international', 'international'],
    'interet_jeu': ['non jeu', 'peu jeu', 'très jeu'],
    'interet_promo': ['non promo', 'peu promo', 'Sensibles aux promos'],
    'action': ['achat', 'recharge', 'roue chance']
}

class SegmentFiltreForm(forms.Form):
    def __init__(self, *args, segment_type='acquisition', **kwargs):
        super().__init__(*args, **kwargs)
        self.segment_type = segment_type
        
        # Common fields
        self.fields['date_debut'] = forms.DateField(
            widget=forms.DateInput(attrs={'type': 'date'}), 
            label="Date de début"
        )
        self.fields['date_fin'] = forms.DateField(
            widget=forms.DateInput(attrs={'type': 'date'}), 
            label="Date de fin"
        )
        
        # Add segment type selector
        self.fields['segment_type'] = forms.ChoiceField(
            choices=[
                ('acquisition', 'Acquisition'),
                ('loyalty', 'Fidélisation')
            ],
            initial=segment_type,
            widget=forms.Select(attrs={'onchange': 'this.form.submit()'}),
            label="Type de segment"
        )
        
        # Common segment fields
        self.fields['rentabilite'] = forms.ChoiceField(
            choices=[('', '---')] + [(v, v) for v in SEGMENTS_POSSIBLES['rentabilite']], 
            required=False
        )
        self.fields['engagement'] = forms.ChoiceField(
            choices=[('', '---')] + [(v, v) for v in SEGMENTS_POSSIBLES['engagement']], 
            required=False
        )
        
        # Only show type_client for acquisition
        if segment_type == 'acquisition':
            self.fields['type_client'] = forms.ChoiceField(
                choices=[('', '---')] + [(v, v) for v in SEGMENTS_POSSIBLES['type_client']], 
                required=False
            )
        
        # Common segment fields
        self.fields['type_interet'] = forms.ChoiceField(
            choices=[('', '---')] + [(v, v) for v in SEGMENTS_POSSIBLES['type_interet']], 
            required=False
        )
        self.fields['interet_international'] = forms.ChoiceField(
            choices=[('', '---')] + [(v, v) for v in SEGMENTS_POSSIBLES['interet_international']], 
            required=False
        )
        self.fields['interet_jeu'] = forms.ChoiceField(
            choices=[('', '---')] + [(v, v) for v in SEGMENTS_POSSIBLES['interet_jeu']], 
            required=False
        )
        self.fields['interet_promo'] = forms.ChoiceField(
            choices=[('', '---')] + [(v, v) for v in SEGMENTS_POSSIBLES['interet_promo']], 
            required=False
        )
        self.fields['action'] = forms.ChoiceField(
            choices=[('', '---')] + [(v, v) for v in SEGMENTS_POSSIBLES['action']], 
            required=False
        )

class UploadSegmentationFilesForm(forms.Form):
    achats_file = forms.FileField(
        label="Fichier Achats (CSV)",
        help_text="Sélectionnez le fichier CSV contenant les données d'achats",
        widget=forms.FileInput(attrs={
            'accept': '.csv',
            'class': 'file-input',
            'aria-label': 'Sélectionner le fichier d\'achats',
            'id': 'achats-file-input'
        })
    )
    recharges_file = forms.FileField(
        label="Fichier Recharges (CSV)",
        help_text="Sélectionnez le fichier CSV contenant les données de recharges",
        widget=forms.FileInput(attrs={
            'accept': '.csv',
            'class': 'file-input',
            'aria-label': 'Sélectionner le fichier de recharges',
            'id': 'recharges-file-input'
        })
    )
    spins_file = forms.FileField(
        label="Fichier Jeux (CSV)",
        help_text="Sélectionnez le fichier CSV contenant les données de jeux (spins)",
        widget=forms.FileInput(attrs={
            'accept': '.csv',
            'class': 'file-input',
            'aria-label': 'Sélectionner le fichier de jeux',
            'id': 'spins-file-input'
        })
    )

    def clean_achats_file(self):
        file = self.cleaned_data.get('achats_file')
        return self._validate_csv_file(file, "achats")

    def clean_recharges_file(self):
        file = self.cleaned_data.get('recharges_file')
        return self._validate_csv_file(file, "recharges")

    def clean_spins_file(self):
        file = self.cleaned_data.get('spins_file')
        return self._validate_csv_file(file, "spins")

    def _validate_csv_file(self, file, file_type):
        if not file:
            raise forms.ValidationError(f"Veuillez télécharger un fichier {file_type}.")
        
        # Vérification de l'extension du fichier
        if not file.name.lower().endswith('.csv'):
            raise forms.ValidationError("Le fichier doit être au format CSV.")
        
        # Vérification du contenu du fichier
        try:
            # Lire les premières lignes pour vérifier le format
            content = file.read().decode('utf-8').splitlines()
            if not content or len(content) < 2:  # Au moins l'en-tête et une ligne de données
                raise forms.ValidationError("Le fichier semble vide ou mal formaté.")
            
            # Vérifier les colonnes obligatoires selon le type de fichier
            headers = content[0].lower().split(',')
            if file_type == 'achats' and not all(col in headers for col in ['msisdn', 'event_date']):
                raise forms.ValidationError("Le fichier d'achats doit contenir les colonnes 'msisdn' et 'event_date'.")
            
            # Remettre le curseur au début du fichier pour une lecture ultérieure
            file.seek(0)
            
        except UnicodeDecodeError:
            raise forms.ValidationError("Le fichier n'est pas un fichier texte valide.")
        
        return file

class UploadChurnFilesForm(forms.Form):
    achats_file = forms.FileField(
        label="Fichier Achats (CSV)",
        help_text="Sélectionnez le fichier CSV contenant les données d'achats",
        widget=forms.FileInput(attrs={
            'accept': '.csv',
            'class': 'file-input',
            'aria-label': 'Sélectionner le fichier d\'achats',
            'id': 'achats-file-input'
        })
    )

    recharges_file = forms.FileField(
        label="Fichier Recharges (CSV)",
        help_text="Sélectionnez le fichier CSV contenant les données de recharges",
        widget=forms.FileInput(attrs={
            'accept': '.csv',
            'class': 'file-input',
            'aria-label': 'Sélectionner le fichier de recharges',
            'id': 'recharges-file-input'
        })
    )
    spins_file = forms.FileField(
        label="Fichier Jeux (CSV)",
        help_text="Sélectionnez le fichier CSV contenant les données de jeux (spins)",
        widget=forms.FileInput(attrs={
            'accept': '.csv',
            'class': 'file-input',
            'aria-label': 'Sélectionner le fichier de jeux',
            'id': 'spins-file-input'
        })
    )

    def clean_achats_file(self):
        file = self.cleaned_data.get('achats_file')
        return self._validate_csv_file(file, "achats")

    def clean_recharges_file(self):
        file = self.cleaned_data.get('recharges_file')
        return self._validate_csv_file(file, "recharges")

    def clean_spins_file(self):
        file = self.cleaned_data.get('spins_file')
        return self._validate_csv_file(file, "spins")

    def _validate_csv_file(self, file, file_type):
        if not file:
            raise forms.ValidationError(f"Veuillez télécharger un fichier {file_type}.")
        
        # Vérification de l'extension du fichier
        if not file.name.lower().endswith('.csv'):
            raise forms.ValidationError("Le fichier doit être au format CSV.")
        
        # Vérification du contenu du fichier
        try:
            # Lire les premières lignes pour vérifier le format
            content = file.read().decode('utf-8').splitlines()
            if not content or len(content) < 2:  # Au moins l'en-tête et une ligne de données
                raise forms.ValidationError("Le fichier semble vide ou mal formaté.")
            
            # Vérifier les colonnes obligatoires selon le type de fichier
            headers = content[0].lower().split(',')
            if file_type == 'achats' and not all(col in headers for col in ['msisdn', 'event_date']):
                raise forms.ValidationError("Le fichier d'achats doit contenir les colonnes 'msisdn' et 'event_date'.")
            
            # Remettre le curseur au début du fichier pour une lecture ultérieure
            file.seek(0)
            
        except UnicodeDecodeError:
            raise forms.ValidationError("Le fichier n'est pas un fichier texte valide.")
        
        return file

class TableFilterForm(forms.Form):
    """
    Formulaire pour le filtrage des tables de données
    """
    def __init__(self, *args, fichiers_disponibles=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Stocker la liste des fichiers disponibles pour le filtrage
        self.fichiers_disponibles = fichiers_disponibles or []
        print("FICHIERS PASSES AU FORM :", fichiers_disponibles)
        # Extraire les types de fichiers uniques
        file_types = sorted(list(set(
            get_file_type(f) for f in self.fichiers_disponibles
            if get_file_type(f) is not None
        )))
        
        # Extraire les mois/années uniques
        months_years = sorted(list(set(
            extract_month_year(f) for f in self.fichiers_disponibles
            if extract_month_year(f) is not None
        )), reverse=True)
        
        # Choix pour le type de fichier
        type_choices = [('', 'Tous les types')] + [(t, t.capitalize()) for t in file_types]
        
        # Choix pour la période
        month_choices = [('', 'Toutes les périodes')] + [(m, m) for m in months_years]
        
        # Champs du formulaire
        self.fields['type_fichier'] = forms.ChoiceField(
            choices=type_choices,
            required=False,
            label="Type de données",
            widget=forms.Select(attrs={
                'class': 'form-select',
                'onchange': 'this.form.submit()'
            })
        )
        
        self.fields['mois'] = forms.ChoiceField(
            choices=month_choices,
            required=False,
            label="Période",
            widget=forms.Select(attrs={
                'class': 'form-select',
                'onchange': 'this.form.submit()'
            })
        )
        
        self.fields['fichier'] = forms.ChoiceField(
            choices=[],
            required=False,
            label="Fichier",
            widget=forms.Select(attrs={
                'class': 'form-select',
                'onchange': 'this.form.submit()'
            })
        )
        
        self.fields['recherche'] = forms.CharField(
            required=False,
            label="Rechercher",
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Rechercher...',
                'aria-label': 'Rechercher dans les données'
            })
        )
    
    def filtrer_fichiers(self, fichiers):
        """
        Filtre la liste des fichiers selon les critères du formulaire.
        
        Args:
            fichiers (list): Liste des noms de fichiers à filtrer
            
        Returns:
            list: Liste des noms de fichiers filtrés selon les critères
        """
        if not fichiers:
            return []
            
        try:
            # Créer une copie de la liste des fichiers pour éviter de modifier l'original
            fichiers_filtres = []
            
            # Récupérer les données du formulaire de manière sécurisée
            form_data = getattr(self, 'cleaned_data', {}) or {}
            
            # Récupérer les critères de filtrage
            type_fichier = form_data.get('type_fichier')
            mois = form_data.get('mois')
            
            # Parcourir chaque fichier et appliquer les filtres
            for fichier in fichiers:
                if not isinstance(fichier, str):
                    continue
                    
                # Vérifier le type de fichier
                type_ok = True
                if type_fichier and type_fichier != '':
                    file_type = get_file_type(fichier)
                    type_ok = file_type is not None and file_type == type_fichier
                
                # Vérifier le mois/année
                mois_ok = True
                if mois and mois != '':
                    file_month = extract_month_year(fichier)
                    mois_ok = file_month is not None and file_month == mois
                
                # Si tous les critères sont satisfaits, ajouter le fichier aux résultats
                if type_ok and mois_ok:
                    fichiers_filtres.append(fichier)
            
            return fichiers_filtres
            
        except Exception as e:
            # En cas d'erreur, logger l'erreur et retourner une liste vide
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erreur lors du filtrage des fichiers: {str(e)}", exc_info=True)
            return []