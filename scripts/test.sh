#!/usr/bin/env bash
# Test GitHub Actions workflows locally with act

set -euo pipefail

source "./scripts/utils/logging.sh"

log_error "act is not installed"
echo ""
echo -e "${GREEN}Install with:${NC}"
echo -e "  ${CYAN}macOS:${NC}  brew install act"
echo -e "  ${CYAN}Linux:${NC}  curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash"
echo -e "  ${CYAN}Gentoo:${NC} echo "dev-util/act ~amd64" >> /etc/portage/package.accept_keywords/act"
echo -e "          emerge -av dev-util/act"
echo ""
exit 1
