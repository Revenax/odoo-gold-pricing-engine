# GitHub Secrets Setup Guide

This guide walks you through setting up all required secrets for automated deployment to EC2.

## Prerequisites

- Access to your GitHub repository with admin/owner permissions
- Access to your EC2 instance via SSH
- Basic knowledge of SSH keys

## Required Secrets

You need to add 4 secrets to your GitHub repository:

1. `EC2_HOST` - Your EC2 instance hostname or IP address
2. `EC2_USER` - SSH username for EC2
3. `EC2_SSH_KEY` - Private SSH key for authentication
4. `EC2_MODULE_PATH` - Full path to the module directory on EC2

---

## Step 1: Navigate to GitHub Secrets

1. Go to your GitHub repository: `https://github.com/YOUR_USERNAME/odoo-gold-pricing-engine`
2. Click on **Settings** (top menu bar)
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click the **New repository secret** button

---

## Step 2: Gather Required Information

Before adding secrets, collect the following information:

### 2.1 Find Your EC2 Host

**Option A: From AWS Console**
- Go to EC2 Dashboard → Instances
- Find your instance → Copy the **Public IPv4 address** or **Public IPv4 DNS**

**Option B: From SSH Connection**
- If you already SSH into EC2, check your connection command:
  ```bash
  ssh user@your-ec2-host.com
  ```
  The part after `@` is your EC2_HOST

**Example values:**
- IP: `54.123.45.67`
- DNS: `ec2-54-123-45-67.compute-1.amazonaws.com`

### 2.2 Find Your EC2 User

Common values based on AMI:
- **Amazon Linux**: `ec2-user`
- **Ubuntu**: `ubuntu`
- **Debian**: `admin` or `debian`
- **RHEL/CentOS**: `ec2-user` or `centos`

**To verify:**
```bash
# When SSH'd into EC2, check:
whoami
```

### 2.3 Find Your Module Path

This is the full path where your `gold_pricing` module is located on EC2.

**Common locations:**
- `/opt/odoo/addons/gold_pricing`
- `/usr/lib/python3/dist-packages/odoo/addons/gold_pricing`
- `/home/odoo/odoo/addons/gold_pricing`
- `~/odoo/addons/gold_pricing` (expanded: `/home/ec2-user/odoo/addons/gold_pricing`)

**To find it:**
```bash
# SSH into EC2 and run:
cd /path/to/your/module
pwd
# Copy the full path shown
```

---

## Step 3: Generate SSH Key (If Needed)

If you don't have an SSH key pair for GitHub Actions, create one:

### 3.1 Generate New SSH Key

On your local machine:

```bash
# Generate a new SSH key (Ed25519 is recommended)
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy

# Or if Ed25519 is not supported, use RSA:
ssh-keygen -t rsa -b 4096 -C "github-actions-deploy" -f ~/.ssh/github_deploy
```

**Important:** When prompted for a passphrase, press Enter to leave it empty (required for automated deployments).

### 3.2 Add Public Key to EC2

Copy the public key to your EC2 instance:

```bash
# Display the public key
cat ~/.ssh/github_deploy.pub

# Copy the entire output (starts with ssh-ed25519 or ssh-rsa)
```

Then SSH into your EC2 instance and add it to authorized_keys:

```bash
# SSH into EC2
ssh EC2_USER@EC2_HOST

# On EC2, add the public key
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "PASTE_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# Test the key works
exit
```

Test the key from your local machine:

```bash
ssh -i ~/.ssh/github_deploy EC2_USER@EC2_HOST
```

If it works without a password, you're good to proceed.

### 3.3 Get Private Key Content

Copy the **entire** private key content:

```bash
# Display the private key (keep this secure!)
cat ~/.ssh/github_deploy

# Copy everything from -----BEGIN to -----END (including those lines)
```

**Security Note:** Never share your private key. Only add it to GitHub Secrets.

---

## Step 4: Add Secrets to GitHub

Now add each secret one by one:

### 4.1 Add EC2_HOST

1. Click **New repository secret**
2. **Name**: `EC2_HOST`
3. **Secret**: Paste your EC2 hostname or IP (e.g., `ec2-54-123-45-67.compute-1.amazonaws.com`)
4. Click **Add secret**

### 4.2 Add EC2_USER

1. Click **New repository secret**
2. **Name**: `EC2_USER`
3. **Secret**: Paste your SSH username (e.g., `ec2-user` or `ubuntu`)
4. Click **Add secret**

### 4.3 Add EC2_SSH_KEY

1. Click **New repository secret**
2. **Name**: `EC2_SSH_KEY`
3. **Secret**: Paste your **entire** private key content:
   ```
   -----BEGIN OPENSSH PRIVATE KEY-----
   b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
   ... (entire key content) ...
   -----END OPENSSH PRIVATE KEY-----
   ```
   **Important:** Include the BEGIN and END lines, and all content in between.
4. Click **Add secret**

### 4.4 Add EC2_MODULE_PATH

1. Click **New repository secret**
2. **Name**: `EC2_MODULE_PATH`
3. **Secret**: Paste the full path to your module (e.g., `/opt/odoo/addons/gold_pricing`)
4. Click **Add secret**

---

## Step 5: Verify Secrets Are Set

1. Go back to **Secrets and variables** → **Actions**
2. You should see all 4 secrets listed:
   - ✅ `EC2_HOST`
   - ✅ `EC2_USER`
   - ✅ `EC2_SSH_KEY`
   - ✅ `EC2_MODULE_PATH`

**Note:** Secret values are hidden for security. You can only see their names.

---

## Step 6: Test the Deployment

1. Make a small change to your code (or just push existing code)
2. Push to the `main` branch:
   ```bash
   git push origin main
   ```
3. Go to GitHub → **Actions** tab
4. Click on the latest workflow run
5. Watch the **check** job complete
6. Watch the **deploy** job (should only run on `main` branch)

### Troubleshooting

**If deployment fails:**

1. **Check workflow logs:**
   - Go to Actions → Click the failed run → Click the failed job
   - Look for error messages

2. **Common issues:**

   - **"EC2_HOST secret is not set"**
     - Secret name is misspelled (must be exactly `EC2_HOST`)
     - Secret was not saved properly

   - **"Permission denied (publickey)"**
     - SSH key not added to EC2's `authorized_keys`
     - Wrong EC2_USER
     - Private key content copied incorrectly (missing BEGIN/END lines)

   - **"No such file or directory" or "Permission denied"**
     - EC2_MODULE_PATH is incorrect
     - Module directory doesn't exist on EC2
     - SSH user doesn't have read/write permissions for the directory
     - Check directory exists: `ls -la /path/to/module`
     - Check permissions: `ls -ld /path/to/module`
     - Fix permissions: `sudo chown -R EC2_USER:EC2_USER /path/to/module`
     - Or use a path the SSH user owns (e.g., `~/odoo/addons/gold_pricing`)

   - **"Fast-forward pull failed"**
     - EC2 has local changes that conflict
     - Need to resolve conflicts on EC2 manually

   - **"Connection timed out" or "ssh: connect to host *** port 22: Connection timed out"**
     - **Most common cause:** EC2 security group doesn't allow SSH from GitHub Actions IPs
     - EC2 instance might be stopped
     - Wrong EC2_HOST (IP or hostname)
     - Network/firewall blocking connection
     - See detailed fix below

3. **Test SSH connection manually:**
   ```bash
   # On your local machine, test the key works:
   ssh -i ~/.ssh/github_deploy EC2_USER@EC2_HOST
   ```

---

## Fixing "Connection Timed Out" Error

This error means GitHub Actions cannot reach your EC2 instance. The most common cause is **EC2 Security Group configuration**.

### Problem

EC2 Security Groups control which IPs can connect to your instance. If your security group only allows SSH from specific IPs (like your office/home IP), GitHub Actions runners (which have dynamic IPs) will be blocked.

### Solution: Update EC2 Security Group

**Option 1: Allow SSH from Anywhere (Quick Fix - Less Secure)**

⚠️ **Warning:** This allows SSH from any IP. Only use for testing or if you have other security measures.

1. **Go to AWS Console:**
   - EC2 Dashboard → **Instances**
   - Select your instance
   - Click **Security** tab → Click security group name

2. **Edit Inbound Rules:**
   - Click **Edit inbound rules**
   - Find SSH rule (port 22)
   - Change **Source** from `My IP` or specific IP to:
     - **Type:** `SSH`
     - **Protocol:** `TCP`
     - **Port range:** `22`
     - **Source:** `0.0.0.0/0` (allows from anywhere)
   - Click **Save rules**

3. **Test Again:**
   - Push to `main` branch
   - Check GitHub Actions logs

**Option 2: Allow GitHub Actions IP Ranges (More Secure)**

GitHub publishes their Actions runner IP ranges. You can allow only those:

1. **Get GitHub Actions IP Ranges:**
   ```bash
   # GitHub Actions IP ranges (updated regularly)
   # Check: https://api.github.com/meta
   # Or use: https://github.com/actions/runner-images/blob/main/images/linux/Ubuntu2004-Readme.md
   ```

2. **Update Security Group:**
   - Add inbound rule for SSH (port 22)
   - **Source:** `140.82.112.0/20` (GitHub Actions CIDR blocks)
   - Add multiple rules for all GitHub IP ranges

   **Note:** GitHub IP ranges change, so this requires periodic updates.

**Option 3: Use AWS Systems Manager Session Manager (Most Secure)**

Instead of SSH, use AWS SSM for secure access without opening port 22:

1. Install SSM agent on EC2 (usually pre-installed on Amazon Linux 2)
2. Configure IAM role with SSM permissions
3. Update GitHub Actions workflow to use `aws ssm start-session` instead of SSH

This is more complex but eliminates the need to open SSH port.

### Verify EC2 Instance Status

1. **Check if instance is running:**
   - AWS Console → EC2 → Instances
   - Status should be **Running** (green)

2. **Check Public IP:**
   - Make sure instance has a **Public IPv4 address**
   - If not, check if it's in a public subnet

3. **Test from your local machine:**
   ```bash
   # If this works, the issue is GitHub Actions IP blocking
   ssh -i ~/.ssh/github_deploy EC2_USER@EC2_HOST
   ```

### Alternative: Use a Bastion Host

If you can't modify the security group, use a bastion host:

1. Create a small EC2 instance with public SSH access
2. Configure GitHub Actions to SSH to bastion first
3. From bastion, SSH to your main EC2 instance

This adds complexity but maintains tighter security.

---

## Security Best Practices

1. **Never commit secrets** to your repository
2. **Use separate SSH keys** for GitHub Actions (don't reuse personal keys)
3. **Rotate keys periodically** (every 90 days recommended)
4. **Limit SSH key access** - only add to the specific EC2 instance needed
5. **Use IAM roles** when possible (more advanced, better security)

---

## Updating Secrets

To update a secret:

1. Go to **Secrets and variables** → **Actions**
2. Click on the secret name
3. Click **Update**
4. Paste new value
5. Click **Update secret**

---

## Removing Secrets

To remove a secret:

1. Go to **Secrets and variables** → **Actions**
2. Click on the secret name
3. Click **Delete**
4. Confirm deletion

**Warning:** Removing secrets will break automated deployment until they're re-added.

---

## Need Help?

If you encounter issues:

1. **Check the GitHub Actions logs** for specific error messages
2. **Verify all secrets are set correctly** (names must match exactly)
3. **Test SSH connection manually** using the same credentials:
   ```bash
   ssh -i ~/.ssh/github_deploy EC2_USER@EC2_HOST
   ```
4. **Verify EC2 Security Group** allows SSH (port 22) from GitHub Actions IPs
   - See "Fixing Connection Timed Out Error" section above
5. **Check EC2 instance status** - ensure it's running and has a public IP
6. **Verify network ACLs** - ensure subnet allows inbound SSH traffic

### Quick Diagnostic Checklist

- [ ] EC2 instance is **Running**
- [ ] EC2 has **Public IPv4 address**
- [ ] Security Group allows **SSH (port 22)** from `0.0.0.0/0` (or GitHub IPs)
- [ ] SSH key is correctly added to EC2 `~/.ssh/authorized_keys`
- [ ] Can SSH from local machine using the same key
- [ ] All GitHub Secrets are set correctly
- [ ] EC2_HOST is correct (IP or hostname)
- [ ] EC2_USER matches the AMI (ec2-user, ubuntu, etc.)
