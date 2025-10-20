#!/usr/bin/env bash
# Test GitHub Actions workflows locally with act

set -euo pipefail

source "./scripts/utils/logging.sh"

##
# Check if act is installed
##
check_act() {
    if ! command -v act &> /dev/null; then
        log_error "act is not installed"
        echo ""
        echo -e "${GREEN}Install with:${NC}"
        echo -e "  ${CYAN}macOS:${NC}  brew install act"
        echo -e "  ${CYAN}Linux:${NC}  curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash"
        echo -e "  ${CYAN}Gentoo:${NC} echo \"dev-util/act ~amd64\" >> /etc/portage/package.accept_keywords/act"
        echo -e "          emerge -av dev-util/act"
        echo ""
        exit 1
    fi

    log_info "act version: $(act --version)"
}

##
# Check for uncommitted changes
##
check_uncommitted() {
    if ! git diff-index --quiet HEAD --; then
        log_warn "You have uncommitted changes"
        echo ""
        echo "Uncommitted changes:"
        git status --short
        echo ""
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Aborting. Commit your changes first for accurate testing."
            exit 0
        fi
    else
        log_info "Working directory clean ✓"
    fi
}

##
# Show usage
##
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] [JOB]

Test GitHub Actions workflows locally using act.

OPTIONS:
    -h, --help          Show this help message
    -l, --list          List all jobs
    -n, --dryrun       Show what would run without executing
    -v, --verbose       Verbose output
    --platform PLATFORM Specify platform (ubuntu-latest, macos-latest)
    --skip-check        Skip uncommitted changes check

JOBS:
    build               Test the build job
    release             Test the release job (requires tag event)
    test-release        Test the release testing job
    all                 Test all jobs (default)

EXAMPLES:
    # List all available jobs
    $0 --list

    # Test build job
    $0 build

    # Test with verbose output
    $0 -v build

    # Dry run to see what would happen
    $0 --dryrun build

    # Test on specific platform
    $0 --platform ubuntu-latest build

    # Skip uncommitted changes check
    $0 --skip-check build

EOF
}

##
# Create event files if they don't exist
##
create_event_files() {
    mkdir -p .github/act-events

    # Push event
    if [ ! -f .github/act-events/push.json ]; then
        cat > .github/act-events/push.json << 'EOF'
{
  "ref": "refs/heads/main",
  "repository": {
    "name": "dip-cli",
    "full_name": "syntlyx/dip-cli"
  }
}
EOF
        log_info "Created .github/act-events/push.json"
    fi

    # Tag push event
    if [ ! -f .github/act-events/tag-push.json ]; then
        cat > .github/act-events/tag-push.json << 'EOF'
{
  "ref": "refs/tags/v2.0.0-alpha.2",
  "repository": {
    "name": "dip-cli",
    "full_name": "syntlyx/dip-cli"
  }
}
EOF
        log_info "Created .github/act-events/tag-push.json"
    fi
}

# Parse arguments
DRY_RUN=""
VERBOSE=""
LIST_JOBS=""
SKIP_CHECK=false
PLATFORM=""
JOB=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -l|--list)
            LIST_JOBS="--list"
            shift
            ;;
        -n|--dryrun)
            DRY_RUN="--dryrun"
            shift
            ;;
        -v|--verbose)
            VERBOSE="--verbose"
            shift
            ;;
        --platform)
            PLATFORM="--matrix os:$2"
            shift 2
            ;;
        --skip-check)
            SKIP_CHECK=true
            shift
            ;;
        *)
            JOB="$1"
            shift
            ;;
    esac
done

##
# Main execution
##
main() {
    log_step "Testing GitHub Actions workflows locally"

    # Check requirements
    check_act

    # Clean build artifacts to avoid conflicts
    log_info "Cleaning build artifacts to avoid parallel execution conflicts..."
    make clean

    # Check for uncommitted changes unless skipped
    if [ "$SKIP_CHECK" = false ]; then
        check_uncommitted
    fi

    # Create event files
    create_event_files

    # List jobs if requested
    if [ -n "$LIST_JOBS" ]; then
        log_step "Available jobs"
        act $LIST_JOBS
        exit 0
    fi

    # Default to empty job (runs all)
    JOB="${JOB:-}"

    # Determine event type and build act command
    EVENT_TYPE="push"  # Default event
    JOB_FLAG=""
    EVENT_FILE=""

    # Add job if specified
    if [ -n "$JOB" ]; then
        case "$JOB" in
            build)
                JOB_FLAG="-j build"
                EVENT_FILE=".github/act-events/push.json"
                ;;
            release)
                JOB_FLAG="-j release"
                EVENT_FILE=".github/act-events/tag-push.json"
                log_warn "Testing release job with tag event"
                ;;
            test-release)
                JOB_FLAG="-j test-release"
                EVENT_FILE=".github/act-events/tag-push.json"
                ;;
            all)
                EVENT_FILE=".github/act-events/push.json"
                ;;
            *)
                log_error "Unknown job: $JOB"
                echo ""
                echo "Available jobs: build, release, test-release, all"
                exit 1
                ;;
        esac
    else
        EVENT_FILE=".github/act-events/push.json"
    fi

    # Limit to single platform for local testing (avoid parallel conflicts)
    if [ -z "$PLATFORM" ]; then
        log_error "Platform flag '--platform' is required to avoid running parallel job conflicts."
        exit 1
    fi

    ACT_CMD="act $EVENT_TYPE $PLATFORM"


    [ -n "$JOB_FLAG" ] && ACT_CMD="$ACT_CMD $JOB_FLAG"

    [ -n "$EVENT_FILE" ] && ACT_CMD="$ACT_CMD -e $EVENT_FILE"

    [ -n "$DRY_RUN" ] && ACT_CMD="$ACT_CMD $DRY_RUN"
    [ -n "$VERBOSE" ] && ACT_CMD="$ACT_CMD $VERBOSE"

    # Show what we're running
    log_step "Running test"
    echo "Command: $ACT_CMD"
    echo ""

    # Execute
    if [ -n "$DRY_RUN" ]; then
        log_info "Dry run - showing what would execute"
    fi

    eval "$ACT_CMD"

    # Summary
    echo ""
    log_step "Test complete"
}

##
# Invoke main
##
main "$@"
