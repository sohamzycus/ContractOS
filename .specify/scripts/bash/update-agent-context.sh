#!/usr/bin/env bash

# Update agent context files with information from plan.md
set -e
set -u
set -o pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

eval $(get_feature_paths)

NEW_PLAN="$IMPL_PLAN"
AGENT_TYPE="${1:-}"

# Agent-specific file paths
CURSOR_FILE="$REPO_ROOT/.cursor/rules/specify-rules.mdc"
AGENTS_FILE="$REPO_ROOT/AGENTS.md"
TEMPLATE_FILE="$REPO_ROOT/.specify/templates/agent-file-template.md"

NEW_LANG=""
NEW_FRAMEWORK=""
NEW_DB=""
NEW_PROJECT_TYPE=""

log_info() { echo "INFO: $1"; }
log_success() { echo "✓ $1"; }
log_error() { echo "ERROR: $1" >&2; }
log_warning() { echo "WARNING: $1" >&2; }

cleanup() {
 local exit_code=$?
 rm -f /tmp/agent_update_*_$$
 rm -f /tmp/manual_additions_$$
 exit $exit_code
}

trap cleanup EXIT INT TERM

validate_environment() {
 if [[ -z "$CURRENT_BRANCH" ]]; then
 log_error "Unable to determine current feature"
 exit 1
 fi
 
 if [[ ! -f "$NEW_PLAN" ]]; then
 log_error "No plan.md found at $NEW_PLAN"
 exit 1
 fi
}

extract_plan_field() {
 local field_pattern="$1"
 local plan_file="$2"
 
 grep "^\*\*${field_pattern}\*\*: " "$plan_file" 2>/dev/null | \
 head -1 | \
 sed "s|^\*\*${field_pattern}\*\*: ||" | \
 sed 's/^[ \t]*//;s/[ \t]*$//' | \
 grep -v "NEEDS CLARIFICATION" | \
 grep -v "^N/A$" || echo ""
}

parse_plan_data() {
 local plan_file="$1"
 
 if [[ ! -f "$plan_file" ]] || [[ ! -r "$plan_file" ]]; then
 log_error "Plan file not found or not readable: $plan_file"
 return 1
 fi
 
 NEW_LANG=$(extract_plan_field "Language/Version" "$plan_file")
 NEW_FRAMEWORK=$(extract_plan_field "Primary Dependencies" "$plan_file")
 NEW_DB=$(extract_plan_field "Storage" "$plan_file")
 NEW_PROJECT_TYPE=$(extract_plan_field "Project Type" "$plan_file")
 
 [[ -n "$NEW_LANG" ]] && log_info "Found language: $NEW_LANG"
 [[ -n "$NEW_FRAMEWORK" ]] && log_info "Found framework: $NEW_FRAMEWORK"
 [[ -n "$NEW_DB" ]] && [[ "$NEW_DB" != "N/A" ]] && log_info "Found database: $NEW_DB"
 [[ -n "$NEW_PROJECT_TYPE" ]] && log_info "Found project type: $NEW_PROJECT_TYPE"
}

get_project_structure() {
 local project_type="$1"
 if [[ "$project_type" == *"web"* ]]; then
 echo "backend/\\nfrontend/\\ntests/"
 else
 echo "src/\\ntests/"
 fi
}

get_commands_for_language() {
 local lang="$1"
 case "$lang" in
 *"Python"*) echo "cd src && pytest && ruff check ." ;;
 *"Rust"*) echo "cargo test && cargo clippy" ;;
 *"JavaScript"*|*"TypeScript"*) echo "npm test && npm run lint" ;;
 *) echo "# Add commands for $lang" ;;
 esac
}

update_agent_file() {
 local target_file="$1"
 local agent_name="$2"
 
 log_info "Updating $agent_name context file: $target_file"
 
 local project_name
 project_name=$(basename "$REPO_ROOT")
 local current_date
 current_date=$(date +%Y-%m-%d)
 
 local target_dir
 target_dir=$(dirname "$target_file")
 [[ ! -d "$target_dir" ]] && mkdir -p "$target_dir"
 
 if [[ ! -f "$target_file" ]]; then
 if [[ ! -f "$TEMPLATE_FILE" ]]; then
 log_error "Template not found at $TEMPLATE_FILE"
 return 1
 fi
 
 local temp_file
 temp_file=$(mktemp)
 cp "$TEMPLATE_FILE" "$temp_file"
 
 local project_structure=$(get_project_structure "$NEW_PROJECT_TYPE")
 local commands=$(get_commands_for_language "$NEW_LANG")
 
 sed -i.bak -e "s|\[PROJECT NAME\]|$project_name|" "$temp_file"
 sed -i.bak -e "s|\[DATE\]|$current_date|" "$temp_file"
 sed -i.bak -e "s|\[ONLY COMMANDS FOR ACTIVE TECHNOLOGIES\]|$commands|" "$temp_file"
 
 rm -f "$temp_file.bak"
 mv "$temp_file" "$target_file"
 log_success "Created new $agent_name context file"
 else
 log_success "Updated existing $agent_name context file"
 fi
}

update_specific_agent() {
 local agent_type="$1"
 case "$agent_type" in
 cursor-agent) update_agent_file "$CURSOR_FILE" "Cursor IDE" ;;
 *) update_agent_file "$AGENTS_FILE" "$agent_type" ;;
 esac
}

main() {
 validate_environment
 log_info "=== Updating agent context files for feature $CURRENT_BRANCH ==="
 
 parse_plan_data "$NEW_PLAN" || exit 1
 
 if [[ -z "$AGENT_TYPE" ]]; then
 log_info "No agent specified, updating cursor-agent..."
 update_specific_agent "cursor-agent"
 else
 update_specific_agent "$AGENT_TYPE"
 fi
 
 log_success "Agent context update completed successfully"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
 main "$@"
fi
