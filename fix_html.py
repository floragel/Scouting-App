import os
import re

base_dir = "/Users/nayl/Desktop/Scouting App"
files_to_process = []
for root, dirs, files in os.walk(base_dir):
    for file in files:
        if file.endswith('.html'):
            files_to_process.append(os.path.join(root, file))

translations = {
    # user_login/signup
    "Authentification": "Authentication",
    "Connexion StanRobotix": "FRC Scouting App Login",
    "Connexion": "Login",
    "Adresse email": "Email Address",
    "Mot de passe oublié ?": "Forgot password?",
    "Mot de passe": "Password",
    "Se connecter": "Log In",
    "Ou continuer avec": "Or continue with",
    "Pas encore de compte ?": "Don't have an account?",
    "Créer un compte": "Create an account",
    "Créer votre compte": "Create your account",
    "Rejoignez l'équipe de scouting StanRobotix.": "Join the FRC Scouting App team.",
    "Prénom": "First Name",
    "Nom": "Last Name",
    "Nom complet": "Full Name",
    "Confirmer le mot de passe": "Confirm Password",
    "Clé d'équipe (optionnel)": "Team Key (optional)",
    "S'inscrire": "Sign Up",
    "Déjà un compte ?": "Already have an account?",
    "Accédez à l'interface de scouting pour gérer les données de match de l'équipe.": "Access the scouting interface to manage team match data.",
    
    # team_onboarding
    "Finalisons votre profil": "Let's complete your profile",
    "Entrez les détails de votre équipe pour accéder aux données de scouting et collaborer avec vos coéquipiers.": "Enter your team details to access scouting data and collaborate with your teammates.",
    "Numéro d'équipe FRC": "FRC Team Number",
    "Code d'accès d'équipe": "Team Access Code",
    "Demandez ce code à l'administrateur de votre équipe.": "Ask your team administrator for this code.",
    "Rejoindre l'équipe": "Join Team",
    "Demande en attente de validation": "Request pending validation",
    "Votre demande a été envoyée. Un administrateur de l'équipe": "Your request has been sent. A team administrator for team",
    "doit approuver votre accès.": "must approve your access.",
    "Besoin d'aide pour trouver votre équipe ?": "Need help finding your team?",
    "Créer une nouvelle équipe": "Create a new team",
    "Erreur lors de la demande.": "Request error.",
    "Erreur réseau.": "Network error.",
    
    # settings
    "Annuler": "Cancel",
    
    # profile hub
    "Équipe Assignée": "Assigned Team",
    "Aucune équipe assignée": "No Assigned Team",
    "Affiliation Officielle": "Official Affiliation",
    "Membre de l'équipe FRC": "Member of FRC Team",
    "Voir les détails de l'équipe": "View team details",
    "Modifier mes infos": "Edit my info",
    "Mettre à jour votre profil et contact": "Update your profile and contact",
    "Paramètres de l'app": "App Settings",
    "Préférences et accessibilité": "Preferences and accessibility",
    "Thème Sombre": "Dark Mode",
    "Déconnexion": "Logout",
    "Dernière connexion: Aujourd'hui à": "Last login: Today at"
}

print(f"Modifying {len(files_to_process)} HTML files...")

for file in files_to_process:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()

    # language
    content = content.replace('lang="fr"', 'lang="en"')
    
    # Brand replacement
    content = content.replace('StanRobotix', 'FRC Scouting App')
    
    # Extra fix 
    content = content.replace('Designed for FRC Scouting App FRC', 'Designed for FRC Scouting App')
    
    # Footer existing replacement
    content = re.sub(r'StanRobotix Hub v[\d\.]+ © \d{4} Team \d+', '© Nayl Lahlou, Team 6622 StanRobotix', content)
    content = re.sub(r'FRC Scouting App(?: Hub)? v[\d\.]+ © \d{4} Team \d+', '© Nayl Lahlou, Team 6622 StanRobotix', content)
    
    # Clean up any missed copyright things specifically the old text "StanRobotix Hub v2.4.0 © 2024 Team 1234" might be affected
    
    # Translations
    for fr, en in translations.items():
        # Because we already replaced 'StanRobotix' with 'FRC Scouting App', we should also test if the translated source has the swapped brand 
        fr_swapped = fr.replace('StanRobotix', 'FRC Scouting App')
        content = content.replace(fr_swapped, en)
        content = content.replace(fr, en)
        
        
    # Apply footer addition if NO copyright string 
    if 'Nayl Lahlou, Team 6622' not in content:
        footer_html = """
    <footer class="h-10 border-t border-slate-200 dark:border-slate-800 bg-background-light dark:bg-slate-950 flex items-center px-6 justify-center shrink-0 mt-auto">
        <p class="text-xs text-slate-500 font-medium">© Nayl Lahlou, Team 6622 StanRobotix</p>
    </footer>
"""
        # Append before </body> unless it's profile_&_settings_edit which has specific structure
        content = content.replace('</body>', footer_html + '\n</body>')

    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)
print("Done modifying.")
