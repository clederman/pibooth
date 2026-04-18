#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Export pictures and counters to a USB drive after an event."""

import os
import sys
import json
import shutil
import os.path as osp
import subprocess
import time


def find_usb_drives():
    """Find mounted USB drives."""
    drives = []
    media_path = "/media"
    if osp.isdir(media_path):
        for user in os.listdir(media_path):
            user_path = osp.join(media_path, user)
            if osp.isdir(user_path):
                for drive in os.listdir(user_path):
                    drive_path = osp.join(user_path, drive)
                    if osp.isdir(drive_path):
                        drives.append(drive_path)
    return drives


def get_counters(config_dir):
    """Read counters from JSON file."""
    json_path = osp.join(config_dir, "counters.json")
    if osp.isfile(json_path):
        with open(json_path, 'r') as fp:
            return json.load(fp)
    return None


def copy_with_progress(src_dir, dst_dir):
    """Copy directory with progress display."""
    files = []
    for root, dirs, filenames in os.walk(src_dir):
        for f in filenames:
            files.append(osp.join(root, f))

    total = len(files)
    if total == 0:
        print("  Aucun fichier à copier.")
        return 0

    copied = 0
    errors = 0
    for i, src_file in enumerate(files, 1):
        rel_path = osp.relpath(src_file, src_dir)
        dst_file = osp.join(dst_dir, rel_path)
        dst_folder = osp.dirname(dst_file)

        if not osp.isdir(dst_folder):
            os.makedirs(dst_folder)

        try:
            shutil.copy2(src_file, dst_file)
            copied += 1
        except (OSError, IOError) as ex:
            print(f"  ERREUR: {rel_path} - {ex}")
            errors += 1

        # Progress bar
        pct = int(i * 100 / total)
        bar = '█' * (pct // 2) + '░' * (50 - pct // 2)
        print(f"\r  [{bar}] {pct}% ({i}/{total})", end='', flush=True)

    print()  # New line after progress bar
    return copied, errors


def verify_copy(src_dir, dst_dir):
    """Verify that all files were copied correctly by comparing sizes."""
    errors = 0
    for root, dirs, filenames in os.walk(src_dir):
        for f in filenames:
            src_file = osp.join(root, f)
            rel_path = osp.relpath(src_file, src_dir)
            dst_file = osp.join(dst_dir, rel_path)

            if not osp.isfile(dst_file):
                print(f"  MANQUANT: {rel_path}")
                errors += 1
            elif osp.getsize(src_file) != osp.getsize(dst_file):
                print(f"  TAILLE DIFFERENTE: {rel_path}")
                errors += 1
    return errors


def main():
    config_dir = osp.expanduser("~/.config/pibooth")
    pictures_dir = osp.expanduser("~/Pictures/pibooth")

    print("=" * 60)
    print("  PIBOOTH - Export de fin d'événement")
    print("=" * 60)
    print()

    # 1. Show counters
    counters = get_counters(config_dir)
    if counters:
        print(f"  Photos prises     : {counters.get('taken', 0)}")
        print(f"  Photos imprimées  : {counters.get('printed', 0)}")
        print(f"  Photos oubliées   : {counters.get('forgotten', 0)}")
        print()
    else:
        print("  Compteurs non trouvés.")
        print()

    # 2. Count files
    if osp.isdir(pictures_dir):
        jpg_files = [f for f in os.listdir(pictures_dir) if f.endswith('.jpg')]
        raw_dir = osp.join(pictures_dir, 'raw')
        raw_count = sum(len(files) for _, _, files in os.walk(raw_dir)) if osp.isdir(raw_dir) else 0
        forget_dir = osp.join(pictures_dir, 'forget')
        forget_count = len(os.listdir(forget_dir)) if osp.isdir(forget_dir) else 0

        print(f"  Photos finales    : {len(jpg_files)}")
        print(f"  Photos brutes     : {raw_count}")
        print(f"  Photos oubliées   : {forget_count}")
        print()
    else:
        print(f"  Dossier {pictures_dir} non trouvé.")
        return 1

    # 3. Find USB drive
    drives = find_usb_drives()
    if not drives:
        print("  Aucune clé USB détectée.")
        print("  Branchez une clé USB et relancez le script.")
        return 1

    print("  Clés USB détectées :")
    for i, drive in enumerate(drives):
        free = shutil.disk_usage(drive).free // (1024 * 1024)
        print(f"    {i + 1}. {drive} ({free} Mo libres)")

    if len(drives) == 1:
        selected = drives[0]
    else:
        try:
            choice = int(input("\n  Choisir la clé (numéro) : ")) - 1
            selected = drives[choice]
        except (ValueError, IndexError):
            print("  Choix invalide.")
            return 1

    # 4. Create export folder on USB
    event_date = time.strftime("%Y-%m-%d")
    export_dir = osp.join(selected, f"pibooth_{event_date}")
    if osp.isdir(export_dir):
        print(f"\n  Le dossier {export_dir} existe déjà.")
        response = input("  Écraser ? (o/N) : ").strip().lower()
        if response != 'o':
            return 1
        shutil.rmtree(export_dir)

    os.makedirs(export_dir)

    # 5. Copy pictures
    print(f"\n  Copie vers {export_dir}...")
    copied, errors = copy_with_progress(pictures_dir, export_dir)

    # 6. Copy counters
    if counters:
        with open(osp.join(export_dir, "counters.json"), 'w') as fp:
            json.dump(counters, fp, indent=2)

    # 7. Create summary
    summary = {
        "date": event_date,
        "photos_prises": counters.get('taken', 0) if counters else 0,
        "photos_imprimees": counters.get('printed', 0) if counters else 0,
        "photos_oubliees": counters.get('forgotten', 0) if counters else 0,
        "fichiers_copies": copied,
    }
    with open(osp.join(export_dir, "resume_evenement.json"), 'w') as fp:
        json.dump(summary, fp, indent=2, ensure_ascii=False)

    # 8. Verify
    print("\n  Vérification de la copie...")
    verify_errors = verify_copy(pictures_dir, export_dir)

    # 9. Sync USB
    print("  Synchronisation clé USB...")
    subprocess.run(["sync"], check=True)

    # 10. Summary
    print()
    print("=" * 60)
    if verify_errors == 0 and errors == 0:
        print("  EXPORT RÉUSSI")
    else:
        print(f"  EXPORT AVEC {verify_errors + errors} ERREUR(S)")
    print(f"  {copied} fichiers copiés vers {export_dir}")
    if counters:
        print(f"  {counters.get('printed', 0)} impressions réalisées")
    print("=" * 60)
    print()
    print("  Vous pouvez retirer la clé USB en toute sécurité.")

    return 0


if __name__ == '__main__':
    sys.exit(main())
