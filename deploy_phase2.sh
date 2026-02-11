#!/bin/bash
# deploy_phase2.sh - Deploy Phase 2 to production state

echo "?? Deploying Phase 2: Core Managers"
echo "===================================="

cd /home/cody/cody-v3/executive-assistant

# Step 1: Install dependencies
echo ""
echo "Step 1: Installing dependencies..."
pip install -r server/requirements.txt

if [ $? -ne 0 ]; then
    echo "? Dependency installation failed"
    exit 1
fi

echo "? Dependencies installed"

# Step 2: Create data directories
echo ""
echo "Step 2: Creating data directories..."
mkdir -p ~/Library/Application\ Support/ExecutiveAssistant/data/{calendar,contacts,notes,documents,templates,config,intelligence}

echo "? Data directories created"

# Step 3: Run tests
echo ""
echo "Step 3: Running tests..."
bash test_phase2.sh

if [ $? -ne 0 ]; then
    echo "? Tests failed - deployment aborted"
    exit 1
fi

echo "? All tests passed"

# Step 4: Backup existing app.py
echo ""
echo "Step 4: Backing up existing files..."
cp server/app.py server/app.py.backup.phase1

echo "? Backup complete"

# Step 5: Git commit (if in git repo)
echo ""
echo "Step 5: Committing to version control..."
if [ -d .git ]; then
    git add .
    git commit -m "Phase 2 Complete: Core Managers
    
- Email manager with multi-account support
- Calendar manager with availability checking
- Contact manager with search
- Note manager with tasks
- Meeting orchestrator
- Document generator (PPT, Memo, Drawings)
- Full function registry with 25+ EA functions
- Updated app.py with function_call integration
"
    echo "? Changes committed to git"
else
    echo "??  Not a git repository - skipping commit"
fi

# Step 6: Summary
echo ""
echo "===================================="
echo "? Phase 2 Deployment Complete!"
echo ""
echo "?? Summary:"
echo "   - 6 Manager modules created"
echo "   - 25+ EA functions implemented"
echo "   - Calendar, Contacts, Notes, Documents operational"
echo "   - Meeting orchestration framework ready"
echo ""
echo "?? Data location:"
echo "   ~/Library/Application Support/ExecutiveAssistant/"
echo ""
echo "?? Next: Ready to push to GitLab"
echo ""