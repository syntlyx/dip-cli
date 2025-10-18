#!/usr/bin/env bash
# Release script - Tag and push a new release
set -euo pipefail

source "./scripts/utils/logging.sh"


##
# Check if we're on main branch
##
check_branch() {
    CURRENT_BRANCH=$(git branch --show-current)
    if [ "$CURRENT_BRANCH" != "main" ]; then
        log_error "Must be on main branch to create a release. Current: $CURRENT_BRANCH"
        exit 1
    fi
    log_info "On main branch ✓"
}

##
# Check for uncommitted changes
##
check_clean() {
    if ! git diff-index --quiet HEAD --; then
        log_error "Uncommitted changes detected. Commit or stash them first."
        git status --short
        exit 1
    fi
    log_info "Working directory clean ✓"
}

##
# Get version from pyproject.toml
##
get_version() {
    if [ ! -f pyproject.toml ]; then
        log_error "pyproject.toml not found"
        exit 1
    fi

    VERSION=$(grep "^version = " pyproject.toml | sed 's/version = "\(.*\)"/\1/')
    if [ -z "$VERSION" ]; then
        log_error "Could not extract version from pyproject.toml"
        exit 1
    fi

    echo "$VERSION"
}

##
# Check if tag already exists
##
check_tag_exists() {
    local tag=$1
    if git rev-parse "$tag" >/dev/null 2>&1; then
        log_error "Tag $tag already exists"
        exit 1
    fi
    log_info "Tag $tag does not exist ✓"
}

##
# Show what will happen
##
show_plan() {
    local version=$1
    local tag="v$version"

    echo ""
    echo "======================================"
    echo "         Release Plan"
    echo "======================================"
    echo "Version:     $version"
    echo "Tag:         $tag"
    echo "Branch:      $(git branch --show-current)"
    echo "Commit:      $(git rev-parse --short HEAD)"
    echo "======================================"
    echo ""
}

##
# Confirm with user
##
confirm() {
    read -p "Proceed with release? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_warn "Release cancelled"
        exit 0
    fi
}

##
# Create and push tag
##
create_tag() {
    local version=$1
    local tag="v$version"

    log_step "Creating tag $tag"

    # Create annotated tag
    git tag -a "$tag" -m "Release $version"

    log_info "Tag created locally ✓"

    # Push tag
    log_step "Pushing tag to remote"
    git push origin "$tag"

    log_info "Tag pushed ✓"
}

##
# Main function
##
main() {
    log_step "Starting release process"

    # Validation
    check_branch
    check_clean

    # Get version
    VERSION=$(get_version)
    TAG="v$VERSION"

    log_info "Version from pyproject.toml: $VERSION"

    # Check tag doesn't exist
    check_tag_exists "$TAG"

    # Show plan
    show_plan "$VERSION"

    # Confirm
    confirm

    # Create and push tag
    create_tag "$VERSION"

    # Success
    echo ""
    log_step "Release process complete! 🎉"
    echo ""
    echo "GitHub Actions will now:"
    echo "  1. Build binaries for all platforms"
    echo "  2. Run tests"
    echo "  3. Create GitHub release"
    echo "  4. Upload binaries"
    echo ""
    log_info "Monitor progress at: https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/actions"
    echo ""
}

##
# Invoke main
##
main "$@"
