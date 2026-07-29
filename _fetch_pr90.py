import urllib.request
import json
import os

# Read token
key_path = "C:/Users/Maison/Desktop/Bounty Hunter/key.txt"
token = None
with open(key_path) as f:
    for line in f:
        if line.startswith("Github_Token="):
            token = line.split("=", 1)[1].strip()
            break

print(f"Token found: {token[:12]}...")

# Fetch PR #90 files
url = "https://api.github.com/repos/mergeos-bounties/BloggerEasy/pulls/90/files"
req = urllib.request.Request(url, headers={
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "BloggerEasy-bot"
})

with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())

print(f"\nTotal files in PR #90: {len(data)}")

total_additions = sum(f.get("additions", 0) for f in data)
total_deletions = sum(f.get("deletions", 0) for f in data)
print(f"Total +/-: +{total_additions}/-{total_deletions}")

for f in data:
    print(f"\n{'='*60}")
    print(f"FILE: {f['filename']} (+{f.get('additions',0)}/-{f.get('deletions',0)})")
    print(f"{'='*60}")
    patch = f.get("patch", "")
    print(patch)

# Save full patches
with open("_pr90_patches.json", "w") as out:
    json.dump(data, out, indent=2)

print("\n\nSaved to _pr90_patches.json")
