#!/usr/bin/env python3
"""
Script de collecte des données des codes législatifs français
depuis l'API Forgejo de git.tricoteuses.fr
"""

import json
import time
import sys
from datetime import datetime
from typing import List, Dict, Optional
import urllib.request
import urllib.error
from pathlib import Path


class ForgejoAPIClient:
    """Client pour l'API Forgejo de git.tricoteuses.fr"""

    BASE_URL = "https://git.tricoteuses.fr/api/v1"

    def __init__(self, rate_limit_delay: float = 0.3):
        self.rate_limit_delay = rate_limit_delay
        self.request_count = 0

    def _make_request(self, url: str, retries: int = 3) -> Optional[Dict]:
        """Effectue une requête HTTP avec retry"""
        for attempt in range(retries):
            try:
                self.request_count += 1
                with urllib.request.urlopen(url, timeout=30) as response:
                    data = json.loads(response.read().decode())
                    time.sleep(self.rate_limit_delay)
                    return data
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None
                print(f"  ⚠️  HTTP Error {e.code} pour {url}, tentative {attempt + 1}/{retries}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                print(f"  ⚠️  Erreur: {e}, tentative {attempt + 1}/{retries}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
        return None

    def fetch_all_repos(self) -> List[Dict]:
        """Récupère la liste de tous les dépôts de l'organisation 'codes'"""
        print("📚 Récupération de la liste des dépôts...")
        all_repos = []
        page = 1

        while True:
            url = f"{self.BASE_URL}/orgs/codes/repos?limit=50&page={page}"
            repos = self._make_request(url)

            if not repos:
                break

            all_repos.extend(repos)
            print(f"  → Page {page}: {len(repos)} dépôts")
            page += 1

        print(f"✅ {len(all_repos)} codes législatifs trouvés\n")
        return all_repos

    def fetch_repo_commits(self, repo_name: str) -> List[Dict]:
        """Récupère tous les commits d'un dépôt"""
        all_commits = []
        page = 1

        while True:
            url = f"{self.BASE_URL}/repos/codes/{repo_name}/commits?limit=100&page={page}"
            commits = self._make_request(url)

            if not commits:
                break

            all_commits.extend(commits)
            page += 1

        return all_commits


class DataProcessor:
    """Transforme les données de l'API en format optimisé pour la visualisation"""

    @staticmethod
    def extract_commit_data(commit: Dict, repo_slug: str) -> Dict:
        """Extrait les données pertinentes d'un commit"""
        # Extraire la première ligne du message (titre)
        message = commit['commit']['message']
        title = message.split('\n')[0]

        # Tronquer si trop long
        if len(title) > 150:
            title = title[:147] + "..."

        # Parser la date et créer un timestamp
        date_str = commit['commit']['author']['date']
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        timestamp = int(dt.timestamp() * 1000)  # Timestamp en millisecondes

        # Récupérer les stats (additions/deletions)
        stats = commit.get('stats', {})
        additions = stats.get('additions', 0)
        deletions = stats.get('deletions', 0)

        return {
            'sha': commit['sha'][:12],  # Hash court
            'date': date_str,
            'ts': timestamp,
            'msg': title,
            'add': additions,
            'del': deletions,
            'url': commit['html_url']
        }

    @staticmethod
    def process_all_data(repos: List[Dict], commits_by_repo: Dict[str, List[Dict]]) -> Dict:
        """Traite toutes les données et calcule les métadonnées globales"""
        all_timestamps = []
        max_additions = 0
        max_deletions = 0
        total_commits = 0

        codes_data = []

        for repo in repos:
            repo_name = repo['name']
            repo_commits = commits_by_repo.get(repo_name, [])

            if not repo_commits:
                continue

            # Traiter chaque commit
            processed_commits = []
            for commit in repo_commits:
                try:
                    commit_data = DataProcessor.extract_commit_data(commit, repo_name)
                    processed_commits.append(commit_data)

                    # Mettre à jour les statistiques globales
                    all_timestamps.append(commit_data['ts'])
                    max_additions = max(max_additions, commit_data['add'])
                    max_deletions = max(max_deletions, commit_data['del'])
                except Exception as e:
                    print(f"  ⚠️  Erreur lors du traitement d'un commit: {e}")
                    continue

            # Trier les commits par timestamp (ordre chronologique)
            processed_commits.sort(key=lambda c: c['ts'])

            total_commits += len(processed_commits)

            codes_data.append({
                'name': repo.get('description', repo_name),
                'slug': repo_name,
                'repo_url': repo['html_url'],
                'total_commits': len(processed_commits),
                'commits': processed_commits
            })

        # Calculer les métadonnées globales
        metadata = {
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'total_codes': len(codes_data),
            'total_commits': total_commits,
            'earliest_commit': min(all_timestamps) if all_timestamps else 0,
            'latest_commit': max(all_timestamps) if all_timestamps else 0,
            'max_additions': max_additions,
            'max_deletions': max_deletions
        }

        # Trier les codes par nom
        codes_data.sort(key=lambda c: c['name'])

        return {
            'metadata': metadata,
            'codes': codes_data
        }


def main():
    """Fonction principale"""
    print("=" * 60)
    print("🇫🇷 Collecte des données - Codes législatifs français")
    print("=" * 60)
    print()

    # Initialiser le client API
    client = ForgejoAPIClient(rate_limit_delay=0.3)

    # Récupérer la liste des dépôts
    repos = client.fetch_all_repos()

    if not repos:
        print("❌ Aucun dépôt trouvé")
        sys.exit(1)

    # Option: limiter aux N premiers codes pour les tests
    # Décommenter la ligne suivante pour tester avec 5 codes
    # repos = repos[:5]
    # print(f"⚠️  Mode test: limité à {len(repos)} codes\n")

    # Récupérer les commits pour chaque dépôt
    print("📥 Récupération des commits...")
    commits_by_repo = {}

    for i, repo in enumerate(repos, 1):
        repo_name = repo['name']
        print(f"  [{i}/{len(repos)}] {repo.get('description', repo_name)}...", end=' ')

        commits = client.fetch_repo_commits(repo_name)
        commits_by_repo[repo_name] = commits

        print(f"✓ {len(commits)} commits")

    print(f"\n✅ {sum(len(c) for c in commits_by_repo.values())} commits au total")
    print(f"📊 {client.request_count} requêtes API effectuées\n")

    # Traiter les données
    print("⚙️  Traitement des données...")
    final_data = DataProcessor.process_all_data(repos, commits_by_repo)

    print(f"✅ {final_data['metadata']['total_commits']} commits traités")
    print(f"📊 Max additions: {final_data['metadata']['max_additions']}")
    print(f"📊 Max deletions: {final_data['metadata']['max_deletions']}\n")

    # Sauvegarder le fichier JSON
    output_dir = Path(__file__).parent.parent / 'docs' / 'data'
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / 'codes_data.json'

    print(f"💾 Sauvegarde dans {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, separators=(',', ':'))

    # Afficher la taille du fichier
    file_size = output_file.stat().st_size
    file_size_mb = file_size / (1024 * 1024)
    print(f"✅ Fichier généré: {file_size_mb:.2f} Mo\n")

    print("=" * 60)
    print("✨ Collecte terminée avec succès!")
    print("=" * 60)


if __name__ == '__main__':
    main()
