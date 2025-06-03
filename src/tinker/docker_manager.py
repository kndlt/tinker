import os
import subprocess
import sys
import time

CONTAINER_NAME = "tinker_sandbox"
TINKER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.tinker'))
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))


def ensure_tinker_dir():
    os.makedirs(TINKER_DIR, exist_ok=True)
    # Also ensure SSH directory exists
    ssh_dir = os.path.join(TINKER_DIR, "ssh")
    os.makedirs(ssh_dir, exist_ok=True)
    # Set proper permissions for SSH directory
    os.chmod(ssh_dir, 0o700)


def container_exists():
    result = subprocess.run([
        "docker", "ps", "-a", "--filter", f"name={CONTAINER_NAME}", "--format", "{{.Names}}"
    ], capture_output=True, text=True)
    return CONTAINER_NAME in result.stdout.strip().splitlines()


def container_running():
    result = subprocess.run([
        "docker", "ps", "--filter", f"name={CONTAINER_NAME}", "--format", "{{.Names}}"
    ], capture_output=True, text=True)
    return CONTAINER_NAME in result.stdout.strip().splitlines()


def start_container():
    ensure_tinker_dir()
    # Create workspace directory
    tinker_workspace_dir = os.path.join(TINKER_DIR, "workspace")
    os.makedirs(tinker_workspace_dir, exist_ok=True)
    
    container_was_created = False
    
    # Use docker-compose to start the container
    if not container_exists():
        subprocess.run([
            "docker", "compose", "up", "-d"
        ], cwd=PROJECT_ROOT, check=True)
        container_was_created = True
    elif not container_running():
        subprocess.run([
            "docker", "compose", "start"
        ], cwd=PROJECT_ROOT, check=True)
    
    # Setup SSH for GitHub if container was just created or SSH not configured
    ssh_dir = os.path.join(TINKER_DIR, "ssh")
    private_key_path = os.path.join(ssh_dir, "id_ed25519")
    
    if container_was_created or not os.path.exists(private_key_path):
        print("🚀 Setting up GitHub SSH authentication...")
        setup_ssh_for_github()


def exec_in_container(cmd):
    full_cmd = ["docker", "exec", CONTAINER_NAME] + cmd
    return subprocess.run(full_cmd, capture_output=True, text=True)


def stop_container():
    if container_running():
        subprocess.run([
            "docker", "compose", "stop"
        ], cwd=PROJECT_ROOT, check=True)


def remove_container():
    if container_exists():
        subprocess.run([
            "docker", "compose", "down"
        ], cwd=PROJECT_ROOT, check=True)


def setup_ssh_for_github():
    """Setup SSH keys for GitHub authentication"""
    ssh_dir = os.path.join(TINKER_DIR, "ssh")
    private_key_path = os.path.join(ssh_dir, "id_ed25519")
    public_key_path = os.path.join(ssh_dir, "id_ed25519.pub")
    
    # Check if SSH key already exists and test connection
    if os.path.exists(private_key_path) and os.path.exists(public_key_path):
        print("✅ SSH key already exists")
        # Test existing connection
        print("🔍 Testing existing GitHub SSH connection...")
        result = exec_in_container(["ssh", "-T", "git@github.com"])
        if "successfully authenticated" in result.stderr:
            print("✅ GitHub SSH authentication is working!")
            return True
        else:
            print("⚠️  Existing SSH key is not working. Regenerating...")
    
    print("🔑 Generating SSH key for GitHub authentication...")
    
    # Generate SSH key in container
    result = exec_in_container([
        "ssh-keygen", "-t", "ed25519", "-C", "tinker@docker",
        "-f", "/home/tinker/.ssh/id_ed25519", "-N", ""
    ])
    
    if result.returncode != 0:
        print(f"❌ Failed to generate SSH key: {result.stderr}")
        return False
    
    # Set proper permissions
    exec_in_container(["chmod", "600", "/home/tinker/.ssh/id_ed25519"])
    exec_in_container(["chmod", "644", "/home/tinker/.ssh/id_ed25519.pub"])
    
    # Read public key to show to user
    result = exec_in_container(["cat", "/home/tinker/.ssh/id_ed25519.pub"])
    if result.returncode == 0:
        public_key = result.stdout.strip()
        print("🔑 SSH Key Generated Successfully!")
        print("=" * 80)
        print("📋 Please add this SSH key to your GitHub account:")
        print("1. 🌐 Go to: https://github.com/settings/ssh/new")
        print("2. 📝 Give it a title like: 'Tinker Docker Container'")
        print("3. 📋 Paste this public key:")
        print()
        print(f"   {public_key}")
        print()
        print("=" * 80)
        print("💡 Tip: You can copy the key above and paste it directly into GitHub")
        print()
        
        # Setup SSH config for GitHub before asking for confirmation
        ssh_config = """Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking no
"""
        
        # Write SSH config
        result = exec_in_container([
            "bash", "-c", f"echo '{ssh_config}' > /home/tinker/.ssh/config"
        ])
        exec_in_container(["chmod", "600", "/home/tinker/.ssh/config"])
        
        # Wait for user confirmation with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                user_input = input("✋ Press Enter after you've added the SSH key to GitHub (or 'skip' to continue without testing): ").strip()
                if user_input.lower() == 'skip':
                    print("⚠️  Skipping SSH connection test. You may need to add the key later.")
                    # Still configure git to use SSH
                    exec_in_container(["git", "config", "--global", "url.git@github.com:.insteadOf", "https://github.com/"])
                    print("✅ Git configured to use SSH for GitHub repositories")
                    return True
                break
            except KeyboardInterrupt:
                print("\n❌ Setup cancelled by user")
                return False
        
        # Test SSH connection
        print("🔍 Testing GitHub SSH connection...")
        result = exec_in_container(["ssh", "-o", "ConnectTimeout=10", "-T", "git@github.com"])
        
        if "successfully authenticated" in result.stderr:
            print("✅ GitHub SSH authentication successful!")
            
            # Configure git to use SSH for GitHub
            exec_in_container(["git", "config", "--global", "url.git@github.com:.insteadOf", "https://github.com/"])
            print("✅ Git configured to use SSH for GitHub repositories")
            
            # Set up git user info if not already configured
            result = exec_in_container(["git", "config", "--global", "user.name"])
            if not result.stdout.strip():
                print("⚙️  Setting up basic git configuration...")
                exec_in_container(["git", "config", "--global", "user.name", "Tinker"])
                exec_in_container(["git", "config", "--global", "user.email", "tinker@docker.local"])
                print("✅ Git user configuration set (you can change this later)")
            
            return True
        else:
            print("⚠️  SSH connection test failed.")
            print("📋 This could mean:")
            print("   1. The SSH key hasn't been added to GitHub yet")
            print("   2. GitHub is temporarily unavailable")
            print("   3. Network connectivity issues")
            print()
            print("🔧 You can test the connection manually later with:")
            print("   docker exec tinker_sandbox ssh -T git@github.com")
            print()
            
            # Still configure git to use SSH for when it works
            exec_in_container(["git", "config", "--global", "url.git@github.com:.insteadOf", "https://github.com/"])
            print("✅ Git configured to use SSH for GitHub repositories")
            
            # Ask if user wants to retry
            try:
                retry = input("🔄 Would you like to retry the connection test? [y/N]: ").strip().lower()
                if retry in ['y', 'yes']:
                    return setup_ssh_connection_test()
            except KeyboardInterrupt:
                print("\n⚠️  Continuing without connection test")
            
            return True
    else:
        print(f"❌ Failed to read public key: {result.stderr}")
        return False


def setup_ssh_connection_test():
    """Helper function to test SSH connection with retries"""
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        print(f"🔍 Testing GitHub SSH connection (attempt {attempt}/{max_retries})...")
        result = exec_in_container(["ssh", "-o", "ConnectTimeout=10", "-T", "git@github.com"])
        
        if "successfully authenticated" in result.stderr:
            print("✅ GitHub SSH authentication successful!")
            return True
        else:
            if attempt < max_retries:
                print(f"❌ Attempt {attempt} failed. Retrying in 2 seconds...")
                time.sleep(2)
            else:
                print("❌ All connection attempts failed")
                print("💡 The SSH key setup is complete, but the connection test failed")
                print("   You can test manually later or check your GitHub SSH key settings")
    
    return False


def ensure_github_ssh():
    """Ensure GitHub SSH authentication is set up"""
    if not container_running():
        print("❌ Container is not running. Please start the container first.")
        return False
    
    return setup_ssh_for_github()


def check_ssh_status():
    """Check the current SSH authentication status for GitHub"""
    if not container_running():
        print("❌ Container is not running. Please start Tinker first.")
        return False
    
    ssh_dir = os.path.join(TINKER_DIR, "ssh")
    private_key_path = os.path.join(ssh_dir, "id_ed25519")
    public_key_path = os.path.join(ssh_dir, "id_ed25519.pub")
    
    print("🔍 Checking SSH authentication status...")
    
    # Check if keys exist
    if os.path.exists(private_key_path) and os.path.exists(public_key_path):
        print("✅ SSH keys found")
        
        # Show public key
        result = exec_in_container(["cat", "/home/tinker/.ssh/id_ed25519.pub"])
        if result.returncode == 0:
            public_key = result.stdout.strip()
            print(f"📋 Public key: {public_key}")
        
        # Test connection
        print("🔍 Testing GitHub connection...")
        result = exec_in_container(["ssh", "-o", "ConnectTimeout=10", "-T", "git@github.com"])
        
        if "successfully authenticated" in result.stderr:
            print("✅ GitHub SSH authentication is working!")
            
            # Check git configuration
            result = exec_in_container(["git", "config", "--global", "url.git@github.com:.insteadOf"])
            if "https://github.com/" in result.stdout:
                print("✅ Git is configured to use SSH for GitHub")
            else:
                print("⚠️  Git is not configured to use SSH for GitHub")
                
            return True
        else:
            print("❌ SSH connection to GitHub failed")
            print("💡 You may need to add the SSH key to your GitHub account")
            return False
    else:
        print("❌ No SSH keys found")
        print("💡 Run Tinker to automatically generate SSH keys")
        return False


def reset_ssh_setup():
    """Reset and regenerate SSH keys for GitHub"""
    if not container_running():
        print("❌ Container is not running. Please start Tinker first.")
        return False
    
    ssh_dir = os.path.join(TINKER_DIR, "ssh")
    
    print("🔄 Resetting SSH setup for GitHub...")
    
    # Remove existing keys
    private_key_path = os.path.join(ssh_dir, "id_ed25519")
    public_key_path = os.path.join(ssh_dir, "id_ed25519.pub")
    
    if os.path.exists(private_key_path):
        os.remove(private_key_path)
        print("🗑️  Removed old private key")
    
    if os.path.exists(public_key_path):
        os.remove(public_key_path)
        print("🗑️  Removed old public key")
    
    # Remove SSH config and known_hosts
    exec_in_container(["rm", "-f", "/home/tinker/.ssh/config"])
    exec_in_container(["rm", "-f", "/home/tinker/.ssh/known_hosts"])
    
    # Generate new keys
    return setup_ssh_for_github()


# Add convenience functions for CLI usage
def ssh_status():
    """Public function to check SSH status - can be called from CLI"""
    return check_ssh_status()


def ssh_reset():
    """Public function to reset SSH setup - can be called from CLI"""
    return reset_ssh_setup()
