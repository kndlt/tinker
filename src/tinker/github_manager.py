import os
import json
from .docker_manager import exec_in_container, container_running


def _ensure_github_cli_ready():
    """Helper function to ensure container is running and GitHub CLI is authenticated"""
    if not container_running():
        print("❌ Container is not running. Please start Tinker first.")
        return False
    
    # Check if authenticated
    auth_result = exec_in_container(["gh", "auth", "status"])
    if auth_result.returncode != 0:
        print("❌ GitHub CLI is not authenticated. Run 'tinker --github-setup' first.")
        return False
    
    return True


def setup_github_cli_auth():
    """Setup GitHub CLI authentication using token or SSH"""
    if not container_running():
        print("❌ Container is not running. Please start Tinker first.")
        return False
    
    print("🔧 Setting up GitHub CLI authentication...")
    
    # Check if GitHub CLI is installed
    result = exec_in_container(["which", "gh"])
    if result.returncode != 0:
        print("❌ GitHub CLI is not installed in the container")
        return False
    
    # Check if already authenticated
    result = exec_in_container(["gh", "auth", "status"])
    if result.returncode == 0:
        print("✅ GitHub CLI is already authenticated!")
        print(result.stdout)
        return True
    
    # Check if GITHUB_TOKEN is available in environment
    token_result = exec_in_container(["printenv", "GITHUB_TOKEN"])
    if token_result.returncode == 0 and token_result.stdout.strip():
        print("🔑 Found GITHUB_TOKEN, attempting token-based authentication...")
        # Use token authentication
        token_auth_result = exec_in_container(["sh", "-c", "echo $GITHUB_TOKEN | gh auth login --with-token"])
        if token_auth_result.returncode == 0:
            print("✅ GitHub CLI authentication successful using token!")
            return True
        else:
            print(f"❌ Token authentication failed: {token_auth_result.stderr}")
    
    print("❌ GitHub CLI authentication requires setup")
    print("💡 To authenticate GitHub CLI, you have two options:")
    print()
    print("1. Using a Personal Access Token (Recommended):")
    print("   - Create a token at: https://github.com/settings/tokens")
    print("   - Required scopes: repo, read:org, read:user, user:email")
    print("   - Add GITHUB_TOKEN=your_token_here to your .env file")
    print("   - Restart the container: docker compose restart")
    print("   - Run: tinker --github-setup")
    print()
    print("2. Manual interactive authentication:")
    print("   - Run: docker exec -it tinker_sandbox gh auth login")
    print("   - Follow the prompts to authenticate via web browser")
    print()
    return False


def check_github_cli_status():
    """Check if GitHub CLI is authenticated"""
    if not container_running():
        print("❌ Container is not running. Please start Tinker first.")
        return False
    
    print("🔍 Checking GitHub CLI authentication status...")
    
    # Check if GitHub CLI is installed
    result = exec_in_container(["which", "gh"])
    if result.returncode != 0:
        print("❌ GitHub CLI is not installed in the container")
        return False
    
    # Check authentication status
    result = exec_in_container(["gh", "auth", "status"])
    if result.returncode == 0:
        print("✅ GitHub CLI is authenticated!")
        print(result.stdout)
        return True
    else:
        print("❌ GitHub CLI is not authenticated")
        print("💡 Run 'tinker --github-setup' to authenticate")
        return False


def list_github_issues(repo, state="open", limit=10):
    """List GitHub issues for a repository"""
    if not _ensure_github_cli_ready():
        return None
    
    print(f"📋 Fetching {state} issues from {repo} (limit: {limit})...")
    
    # Use gh CLI to list issues
    cmd = [
        "gh", "issue", "list",
        "--repo", repo,
        "--state", state,
        "--limit", str(limit),
        "--json", "number,title,state,createdAt,updatedAt,url,labels,assignees"
    ]
    
    result = exec_in_container(cmd)
    
    if result.returncode == 0:
        try:
            issues = json.loads(result.stdout)
            print(f"✅ Found {len(issues)} {state} issues:")
            print("=" * 80)
            
            for issue in issues:
                labels = ", ".join([label["name"] for label in issue.get("labels", [])])
                assignees = ", ".join([assignee["login"] for assignee in issue.get("assignees", [])])
                
                print(f"#{issue['number']}: {issue['title']}")
                print(f"  State: {issue['state']}")
                print(f"  Created: {issue['createdAt'][:10]}")
                print(f"  Updated: {issue['updatedAt'][:10]}")
                if labels:
                    print(f"  Labels: {labels}")
                if assignees:
                    print(f"  Assignees: {assignees}")
                print(f"  URL: {issue['url']}")
                print("-" * 40)
            
            return issues
        except json.JSONDecodeError:
            print("❌ Failed to parse GitHub CLI response")
            print(f"Raw output: {result.stdout}")
            return None
    else:
        print(f"❌ Failed to fetch issues: {result.stderr}")
        return None


def get_github_issue(repo, issue_number):
    """Get specific GitHub issue details"""
    if not _ensure_github_cli_ready():
        return None
    
    print(f"📋 Fetching issue #{issue_number} from {repo}...")
    
    # Use gh CLI to get issue details
    cmd = [
        "gh", "issue", "view", str(issue_number),
        "--repo", repo,
        "--json", "number,title,body,state,createdAt,updatedAt,url,labels,assignees,author"
    ]
    
    result = exec_in_container(cmd)
    
    if result.returncode == 0:
        try:
            issue = json.loads(result.stdout)
            print("✅ Issue details:")
            print("=" * 80)
            print(f"#{issue['number']}: {issue['title']}")
            print(f"Author: {issue['author']['login']}")
            print(f"State: {issue['state']}")
            print(f"Created: {issue['createdAt'][:10]}")
            print(f"Updated: {issue['updatedAt'][:10]}")
            
            labels = ", ".join([label["name"] for label in issue.get("labels", [])])
            if labels:
                print(f"Labels: {labels}")
            
            assignees = ", ".join([assignee["login"] for assignee in issue.get("assignees", [])])
            if assignees:
                print(f"Assignees: {assignees}")
            
            print(f"URL: {issue['url']}")
            print("\nDescription:")
            print("-" * 40)
            print(issue.get('body', 'No description provided'))
            print("=" * 80)
            
            return issue
        except json.JSONDecodeError:
            print("❌ Failed to parse GitHub CLI response")
            print(f"Raw output: {result.stdout}")
            return None
    else:
        print(f"❌ Failed to fetch issue: {result.stderr}")
        return None


def search_github_issues(repo, query, state="open", limit=10):
    """Search GitHub issues for a repository"""
    if not _ensure_github_cli_ready():
        return None
    
    print(f"🔍 Searching for '{query}' in {state} issues from {repo}...")
    
    # Use gh CLI to search issues
    cmd = [
        "gh", "issue", "list",
        "--repo", repo,
        "--state", state,
        "--search", query,
        "--limit", str(limit),
        "--json", "number,title,state,createdAt,updatedAt,url,labels,assignees"
    ]
    
    result = exec_in_container(cmd)
    
    if result.returncode == 0:
        try:
            issues = json.loads(result.stdout)
            print(f"✅ Found {len(issues)} issues matching '{query}':")
            print("=" * 80)
            
            for issue in issues:
                labels = ", ".join([label["name"] for label in issue.get("labels", [])])
                assignees = ", ".join([assignee["login"] for assignee in issue.get("assignees", [])])
                
                print(f"#{issue['number']}: {issue['title']}")
                print(f"  State: {issue['state']}")
                print(f"  Created: {issue['createdAt'][:10]}")
                print(f"  Updated: {issue['updatedAt'][:10]}")
                if labels:
                    print(f"  Labels: {labels}")
                if assignees:
                    print(f"  Assignees: {assignees}")
                print(f"  URL: {issue['url']}")
                print("-" * 40)
            
            return issues
        except json.JSONDecodeError:
            print("❌ Failed to parse GitHub CLI response")
            print(f"Raw output: {result.stdout}")
            return None
    else:
        print(f"❌ Failed to search issues: {result.stderr}")
        return None


def create_github_issue(repo, title, body="", labels=None, assignees=None):
    """Create a new GitHub issue"""
    if not _ensure_github_cli_ready():
        return None
    
    print(f"📝 Creating new issue in {repo}...")
    
    # Build command
    cmd = ["gh", "issue", "create", "--repo", repo, "--title", title]
    
    if body:
        cmd.extend(["--body", body])
    
    if labels:
        if isinstance(labels, list):
            labels = ",".join(labels)
        cmd.extend(["--label", labels])
    
    if assignees:
        if isinstance(assignees, list):
            assignees = ",".join(assignees)
        cmd.extend(["--assignee", assignees])
    
    result = exec_in_container(cmd)
    
    if result.returncode == 0:
        issue_url = result.stdout.strip()
        print(f"✅ Issue created successfully!")
        print(f"🔗 URL: {issue_url}")
        return issue_url
    else:
        print(f"❌ Failed to create issue: {result.stderr}")
        return None
