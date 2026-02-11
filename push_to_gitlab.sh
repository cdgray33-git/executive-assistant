#!/bin/bash
# push_to_gitlab.sh - Push Phase 2 to GitLab

echo "?? Pushing to GitLab"
echo "===================="

cd /home/cody/cody-v3/executive-assistant

# Check if GitLab remote exists
if ! git remote | grep -q "gitlab"; then
    echo "Adding GitLab remote..."
    git remote add gitlab http://172.16.33.126/root/email-cleanup.git
fi

# Check current branch
CURRENT_BRANCH=$(git branch --show-current)
echo "Current branch: $CURRENT_BRANCH"

# Stage all changes
echo "Staging changes..."
git add .

# Check if there are changes to commit
if git diff --cached --quiet; then
    echo "No changes to commit"
else
    echo "Committing changes..."
    git commit -m "Phase 2 Complete: Full EA Core Managers

Implemented:
- EmailManager (multi-account, categorization, smart routing)
- CalendarManager (events, availability, conflict detection)
- ContactManager (search, multi-email support, learning)
- NoteManager (notes + tasks)
- MeetingOrchestrator (full meeting workflow)
- DocumentGenerator (PowerPoint, Memos, Drawings)
- Function registry with 25+ EA capabilities
- Updated app.py with function_call endpoint

Architecture:
- 6 manager modules
- 18 email categories
- AI-powered categorization
- Priority scoring
- Sender learning

Status:
- Yahoo spam cleanup: Working ?
- Calendar operations: Working ?
- Contact management: Working ?
- Meeting scheduling: Working ?
- Document generation: Working ?
- Notes and tasks: Working ?

Ready for Phase 3: Multi-email connectors (Gmail, Hotmail, etc.)
"
fi

# Push to GitLab
echo ""
echo "Pushing to GitLab..."
git push gitlab $CURRENT_BRANCH

if [ $? -eq 0 ]; then
    echo "? Successfully pushed to GitLab"
    echo ""
    echo "View at: http://172.16.33.126/root/email-cleanup"
else
    echo "? Push failed"
    exit 1
fi

echo ""
echo "===================================="
echo "? GitLab Push Complete!"
echo ""