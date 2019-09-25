#!/bin/bash

if ! echo "$-" | grep -q i; then
    return 0
fi

have() {
    for NAME; do
        if command -v "$NAME" >/dev/null; then
            return 0
        fi
    done

    echo "* Missing: $*" >&2
    return 1
}

child_dir="$(readlink -e "$(dirname "${BASH_SOURCE[0]}")")"
abs_home_dir="$(readlink -e "$HOME")"
is_child_home_dir=N

if [ "$child_dir" = "$abs_home_dir" ]; then
    is_child_home_dir=Y
fi

for child in "${BASH_SOURCE[0]}".*; do
    if [ -e "$child" ]; then
        # shellcheck source=/dev/null
        . "$child_dir/$(basename "$child")"

        if [ "$is_child_home_dir" = Y ]; then
            # shellcheck disable=SC2088
            child="~/${child##$abs_home_dir/}"
        fi

        echo "* Loaded: $child" >&2
    fi
done

shopt -s autocd dirspell histappend
alias -- -='cd -'
alias ..='cd ..'

have fd
have dircolors && eval "$("$NAME" -b)"
have lesspipe lesspipe.sh && eval "$("$NAME")"

export HISTCONTROL=ignoredups
export LESS='--tabs=4 --clear-screen --LONG-PROMPT --RAW-CONTROL-CHARS --ignore-case'
export PROMPT_DIRTRIM=2
export PYTHONDONTWRITEBYTECODE=x

# Color man pages.
export LESS_TERMCAP_mb=$'\e[1;31m' # begin bold
export LESS_TERMCAP_md=$'\e[1;33m' # begin blink
export LESS_TERMCAP_so=$'\e[01;44;37m' # begin reverse video
export LESS_TERMCAP_us=$'\e[01;37m' # begin underline
export LESS_TERMCAP_me=$'\e[0m' # reset bold/blink
export LESS_TERMCAP_se=$'\e[0m' # reset reverse video
export LESS_TERMCAP_ue=$'\e[0m' # reset underline

stty -ixon # Allow `bind -q forward-search-history`.

bind 'set bind-tty-special-chars Off'
bind 'set completion-ignore-case On'
bind 'set expand-tilde Off'
bind 'set mark-symlinked-directories On'
bind 'set visible-stats On'

bind '"\e[1;5C": forward-word' # ctrl-right
bind '"\e[1;5D": backward-word' # ctrl-left
bind '"\e[3;5~": kill-word' # ctrl-delete

color_off='\e[0m'
yellow='\e[0;33m'

if [ -n "${BASHRC_CUSTOM_LOCATION:-}" ]; then
    host_prompt=" \[$yellow\]$BASHRC_CUSTOM_LOCATION\[$color_off\]"
elif [ -n "${SSH_CLIENT:-}" ] || [ -n "${SSH_TTY:-}" ]; then
    host_prompt=" \[$yellow\]\\u@\\h\[$color_off\]"
else
    host_prompt=
fi

if have nano; then
    alias nano='nano -Sw'
    export EDITOR="$NAME" GIT_EDITOR="$NAME"
fi

if have show.sh; then
    # shellcheck disable=SC2139
    alias s="$NAME -p dir=-Fh -p dir=--group-directories-first -p dir=--dereference-command-line-symlink-to-dir"
    export PAGER="$NAME" GIT_PAGER="$NAME"
fi

if have ag; then
    if [ -n "$PAGER" ]; then
        # shellcheck disable=SC2139
        alias f="$NAME --follow --hidden --pager \"$PAGER\""
    else
        # shellcheck disable=SC2139
        alias f="$NAME --follow --hidden"
    fi
fi

if have git; then
    c() {
        local cached
        cached=$(git diff --cached --name-only | wc -l)

        if  [ $# -eq 0 ] && [ "$cached" -eq 0 ]; then
            git commit -a
        else
            git commit "$@"
        fi
    }

    alias g=git
    alias a='g add'
    alias b='g branch -vv'
    alias d='g diff'
    alias h='g blame --date=short'
    alias j='g stash'
    alias l='g log --graph --pretty="tformat:%C(yellow)%h%C(reset) -- %s %C(green)%ai %C(cyan)%aN%C(blue bold)%d"'
    alias p='g push'
    alias r='g checkout'
    alias t='g status'
    alias v='g pull'

    if command -v _completion_loader >/dev/null; then
        _completion_loader git
    fi

    if ! command -v __git_complete >/dev/null; then
        echo '* Missing: git Bash completion: https://github.com/git/git/blob/master/contrib/completion/git-completion.bash (or apt "bash-completion", or load order in .bashrc)' >&2
    else
        __git_complete g _git
        __git_complete a _git_add
        __git_complete b _git_branch
        __git_complete c _git_commit
        __git_complete d _git_diff
        __git_complete h __gitcomp
        __git_complete j _git_stash
        __git_complete l _git_log
        __git_complete p _git_push
        __git_complete r _git_checkout
        __git_complete t _git_status
        __git_complete v _git_pull
    fi

    git_cache_file="$child_dir/$(basename "${BASH_SOURCE[0]}")-cached"

    if [ ! -e "$git_cache_file" ]; then
        case "$(git rebase -h 2>&1)" in
            *--rebase-merges*)
                git config --global pull.rebase merges;;
            *--preserve-merges*)
                git config --global pull.rebase preserve;;
            *)
                git config --global --bool pull.rebase true;;
        esac

        git config --global pager.status true
        > "$git_cache_file"
    fi

    export GIT_PS1_SHOWSTASHSTATE=x
    export GIT_PS1_STATESEPARATOR=

    if ! command -v __git_ps1 >/dev/null; then
        echo '* Missing: git prompt: https://github.com/git/git/blob/master/contrib/completion/git-prompt.sh' >&2
    else
        git_prompt="\[\e[0;32m\]\$(__git_ps1 ' %s')\[$color_off\]"
    fi
fi

_job_count_ps1() {
    local jobs
    jobs=$(jobs -p -r -s | wc -l)
    [ "$jobs" -gt 0 ] && echo " $jobs"
}

if [ -z "${BASHRC_KEEP_PROMPT:-}" ]; then
    export PS1="\[\e[1;34m\]\w\[$color_off\]$host_prompt$git_prompt\[\e[1;31m\]\$(_job_count_ps1)\[$color_off\]\\$ "
fi
