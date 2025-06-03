# Tinker - Phase 2.4

Tinker is a virtual engineer that runs inside host machine and uses a docker container to perform tasks.

In Phase 2.4, I want to give it ability to perform `git` commands.

## Phase 2.4 Tasks

- [ ] Ensure git is installed in the Docker container (already available based on Phase 2.1)
- [ ] Test basic git operations within the container workspace
- [ ] Create tasks to validate git functionality:
  - [ ] `git init` - Initialize a new repository
  - [ ] `git config` - Set user name and email
  - [ ] `git add` - Stage files for commit
  - [ ] `git commit` - Create commits
  - [ ] `git status` - Check repository status
  - [ ] `git log` - View commit history
  - [ ] `git branch` - Create and manage branches
  - [ ] `git checkout` - Switch branches
  - [ ] `git merge` - Merge branches
- [ ] Test git with remote repositories:
  - [ ] `git clone` - Clone repositories
  - [ ] `git push` - Push changes to remote
  - [ ] `git pull` - Pull changes from remote
  - [ ] `git fetch` - Fetch remote changes
- [ ] Handle git authentication (SSH keys, tokens) within the container
- [ ] Document git workflow and limitations within the Docker environment

## Implementation Notes

Since git is already installed in the container (from Phase 2.1), the main work will be:
1. Creating test tasks to validate git operations
2. Ensuring proper git configuration within the container
3. Testing git workflows end-to-end
4. Documenting any limitations or setup requirements

## Safety Considerations

- Git operations are safely contained within the Docker environment
- Repository cloning and operations happen in `/home/tinker` (mounted from `.tinker/workspace`)
- No direct access to host git repositories unless explicitly mounted