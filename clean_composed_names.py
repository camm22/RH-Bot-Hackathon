#!/usr/bin/env python
"""
Script to remove employees with composed names from the database
This will make AI formatting much easier by keeping only simple names
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import CustomUser

def has_composed_name(user):
    """
    Check if a user has a composed name (multiple first names or last names)
    """
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    
    # Check for multiple first names (spaces in first_name)
    if len(first_name.split()) > 1:
        return True
    
    # Check for multiple last names (spaces in last_name)
    if len(last_name.split()) > 1:
        return True
    
    # Check for hyphenated names
    if '-' in first_name or '-' in last_name:
        return True
    
    return False

def simplify_name(name):
    """
    Simplify a composed name to just the first part
    """
    if not name:
        return name
    
    # Split by spaces and hyphens
    parts = name.replace('-', ' ').split()
    
    # Return just the first part
    return parts[0] if parts else name

def main():
    print("🔍 Scanning database for employees with composed names...")
    
    # Get all users
    all_users = CustomUser.objects.all()
    print(f"📊 Total employees in database: {all_users.count()}")
    
    # Find users with composed names
    composed_name_users = []
    for user in all_users:
        if has_composed_name(user):
            composed_name_users.append(user)
    
    print(f"\n👥 Found {len(composed_name_users)} employees with composed names:")
    
    # Display the users that will be simplified
    for user in composed_name_users:
        old_first = user.first_name
        old_last = user.last_name
        new_first = simplify_name(old_first)
        new_last = simplify_name(old_last)
        print(f"  - {old_first} {old_last} → {new_first} {new_last} ({user.employee_id or user.id}) - {user.departement}")
    
    if not composed_name_users:
        print("✅ No employees with composed names found. Database is already clean!")
        return
    
    # Ask for confirmation
    print(f"\n⚠️  This will SIMPLIFY the names of {len(composed_name_users)} employees.")
    print("   Composed names will be reduced to their first part only.")
    confirmation = input("Are you sure you want to proceed? Type 'YES' to confirm: ")
    
    if confirmation != 'YES':
        print("❌ Operation cancelled.")
        return
    
    print("\n✂️  Simplifying composed names...")
    
    # Simplify the names
    updated_count = 0
    for user in composed_name_users:
        old_first = user.first_name
        old_last = user.last_name
        
        user.first_name = simplify_name(old_first)
        user.last_name = simplify_name(old_last)
        user.save()
        
        print(f"  Updated: {old_first} {old_last} → {user.first_name} {user.last_name}")
        updated_count += 1
    
    print(f"\n✅ Successfully simplified {updated_count} employee names!")
    
    # Show final count
    remaining_users = CustomUser.objects.all().count()
    print(f"📊 Total employees in database: {remaining_users}")
    
    print("\n🎉 Database cleanup complete! All employees now have simple names.")
    print("   This should eliminate Azure AI formatting issues with split names.")

if __name__ == "__main__":
    main() 