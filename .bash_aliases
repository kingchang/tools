#!/bin/bash

if [[ ! "$-" =~ 'i' ]]; then
    return 0
fi

_warn() {
    echo "* $@" >&2
}

_have() {
    for NAME; do
        LOCATION=$(which $NAME 2> /dev/null)

        if [ -n "$LOCATION" ]; then
            eval "HAVE_$(echo $NAME | tr '[:lower:]-' '[:upper:]_')='$LOCATION'"
            return 0
        fi
    done

    _warn "Missing: $@"
    return 1
}

for bashrc_child in $(ls -1 "$BASH_SOURCE".* 2> /dev/null); do
    source "$bashrc_child"
    _warn "Loaded: $bashrc_child"
done

shopt -s cdspell checkwinsize histappend

alias -- -='cd -'
alias ..='cd ..'
alias ...='cd ../..'

_have dircolors && eval "$($NAME -b)"
_have lesspipe && eval "$($NAME)"

export ANSIBLE_NOCOWS=x
export HISTCONTROL=ignoreboth
export LESS='-x4 -c -M -R -i'
export PROMPT_DIRTRIM=2
export PYTHONDONTWRITEBYTECODE=x

# Color manual pages.
export LESS_TERMCAP_mb=$'\e[1;31m'     # begin bold
export LESS_TERMCAP_md=$'\e[1;33m'     # begin blink
export LESS_TERMCAP_so=$'\e[01;44;37m' # begin reverse video
export LESS_TERMCAP_us=$'\e[01;37m'    # begin underline
export LESS_TERMCAP_me=$'\e[0m'        # reset bold/blink
export LESS_TERMCAP_se=$'\e[0m'        # reset reverse video
export LESS_TERMCAP_ue=$'\e[0m'        # reset underline

_color_off='\e[0m'
_yellow='\e[0;33m'
_green='\e[0;32m'
_b_red='\e[1;31m'
_b_blue='\e[1;34m'

# Allow `bind -q forward-search-history`.
stty -ixon

bind 'set bind-tty-special-chars Off'
bind 'set completion-ignore-case On'
bind 'set expand-tilde Off'
bind 'set mark-symlinked-directories On'
bind 'set visible-stats On'

bind '"\e[1;5C": forward-word'       # ctrl-right
bind '"\e[1;5D": backward-word'      # ctrl-left
bind '"\e[3;5~": kill-word'          # ctrl-delete
bind '"\e[2;5~": backward-kill-word' # ctrl-insert

if test -n "$DESKTOP_SESSION" && _have gnome-keyring-daemon; then
    eval "$($NAME --start)"
fi

if [ -n "$BASHRC_CUSTOM_LOCATION" ]; then
    _prompt="\[$_yellow\]$BASHRC_CUSTOM_LOCATION\[$_color_off\] "
elif [ -n "$SSH_CLIENT" -o -n "$SSH_TTY" ]; then
    _prompt="\[$_yellow\]\\u@\\h\[$_color_off\] "
else
    _prompt=
fi

if _have micro nano; then
    export EDITOR="$NAME"
    export GIT_EDITOR="$NAME"
fi

if _have show; then
    alias s="$NAME -p dir:-Fh -p dir:--color=auto -p dir:--group-directories-first"
    export PAGER="$NAME"
fi

if _have ag; then
    if [ -n "$PAGER" ]; then
        alias f="$NAME --follow --pager \"$PAGER\""
    else
        alias f="$NAME --follow"
    fi
fi

if _have git; then
    _load_git_completions() {
        if type -t _completion_loader > /dev/null; then
            _completion_loader git
        fi

        __git_complete sa _git_add
        __git_complete sb _git_branch
        __git_complete sc _git_commit
        __git_complete sd _git_diff
        __git_complete sh __gitcomp
        __git_complete sl _git_log
        __git_complete sp _git_push
        __git_complete sr _git_checkout
        __git_complete ss _git_pull
        __git_complete st _git_status
    }

    sc() {
        local cached=$(git diff --cached --name-only | wc -l)

        if  [ $# -eq 0 -a $cached -eq 0 ]; then
            git commit -a
        else
            git commit "$@"
        fi
    }

    alias sa='git add "$@"'
    alias sb='git branch -vv "$@"'
    alias sd='git diff "$@"'
    alias sh='git blame --date=short "$@"'
    alias sl='git log --graph --pretty="tformat:%C(yellow)%h%C(reset) -- %s %C(green)%ai %C(cyan)%aN%C(blue bold)%d" "$@"'
    alias sp='git push "$@"'
    alias sr='git checkout "$@"'
    alias ss='git pull "$@"'
    alias st='git status "$@"'

    git config --global push.default simple
    git config --global branch.autosetuprebase always

    export GIT_PS1_SHOWDIRTYSTATE=x
    export GIT_PS1_SHOWSTASHSTATE=x
    export GIT_PS1_SHOWUNTRACKEDFILES=x

    for ALIAS in sa sb sc sd sh sl sp sr ss st; do
        eval "_${ALIAS}() { _load_git_completions; }"
        eval "complete -F _${ALIAS} ${ALIAS}"
    done

    if ! type -t __git_ps1 > /dev/null; then
        _warn "Missing: https://github.com/git/git/blob/master/contrib/completion/git-prompt.sh"
        _color_git_ps1() {
            :
        }
    else
        _color_git_ps1() {
            local ps1=$(__git_ps1 "%s")
            [ -n "$ps1" ] && echo "$ps1 "
        }
    fi

    _prompt="$_prompt\[$_green\]\$(_color_git_ps1)\[$_color_off\]"
fi

_jobs_nr_ps1() {
    local jobs=$(jobs | wc -l)
    [ $jobs -gt 0 ] && echo " $jobs"
}

if [ -z "$BASHRC_KEEP_PROMPT" ]; then
    export PS1="$_prompt\[$_b_blue\]\w\[$_color_off\]\[$_b_red\]\$(_jobs_nr_ps1)\[$_color_off\] \\$ "
fi
