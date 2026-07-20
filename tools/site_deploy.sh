# Shared staticrypt-encrypt + GitHub Pages deploy for workspace project sites.
#
# Source this from a project build.sh AFTER PROJECT_DIR is set:
#     SITE_TITLE="ML and Deterrence"
#     source "$PROJECT_DIR/../../research-kit/tools/site_deploy.sh"
#
# Required:
#   PROJECT_DIR  absolute path to the project (its build.sh dir)
#   SITE_TITLE   staticrypt login-page title
# Optional:
#   SITE_GATED         1 (default) = staticrypt-encrypt; 0 = deploy build/site plaintext
#   SITE_REMEMBER_DAYS staticrypt --remember duration (default 365)
#   SITE_INSTRUCTIONS  login-prompt text (has a default)
#
# Provides: sk_encrypt_site, sk_deploy_site
#
# Both the autofill guard and the per-project remember-key namespacing live here
# ONCE, so every workspace site gets them identically (no per-build.sh drift).
# Why they are needed: all sites are served from the single hsigstad.github.io
# origin, so the browser's password manager AND staticrypt's localStorage key
# them together. Without these fixes the browser autofills one site's saved
# password onto every other, and logging into one site evicts another's
# remembered login.

sk__repo() {
    # Derive "<owner>/<repo>" from the origin remote (ssh or https form).
    git -C "$PROJECT_DIR" remote get-url origin 2>/dev/null \
        | sed -E 's#(git@github\.com:|https://github\.com/)##; s#\.git$##'
}

sk_encrypt_site() {
    local site_dir="$PROJECT_DIR/build/site"
    local out_dir="$PROJECT_DIR/build/site-encrypted"
    local pw_file="$PROJECT_DIR/.site-password"
    [[ -d "$site_dir" ]] || { echo "ERROR: $site_dir missing. Build the site first."; exit 1; }
    local pw="${STATICRYPT_PASSWORD:-}"
    [[ -z "$pw" && -f "$pw_file" ]] && pw="$(tr -d '\n' < "$pw_file")"
    [[ -n "$pw" ]] || { echo "ERROR: set STATICRYPT_PASSWORD in env or write the password to $pw_file"; exit 1; }

    echo ""
    echo "=== Encrypting site -> build/site-encrypted/ ==="
    rm -rf "$out_dir"
    # staticrypt resolves --config relative to CWD, so run from PROJECT_DIR
    # (subshell keeps the caller's CWD untouched).
    ( cd "$PROJECT_DIR"
      STATICRYPT_PASSWORD="$pw" npx --yes staticrypt "$site_dir" \
        --recursive \
        --directory "$out_dir" \
        --config "build/.staticrypt.json" \
        --short \
        --template-title "${SITE_TITLE:-Project site}" \
        --template-instructions "${SITE_INSTRUCTIONS:-Enter the shared password to access the site.}" \
        --remember "${SITE_REMEMBER_DAYS:-365}" \
        >/dev/null )
    if [[ -d "$out_dir/site" ]]; then
        mv "$out_dir/site"/* "$out_dir/site"/.[!.]* "$out_dir/" 2>/dev/null || true
        rmdir "$out_dir/site"
    fi
    # (1) mark the staticrypt password field new-password so the browser stops
    #     autofilling one site's saved password onto the others; (2) namespace
    #     staticrypt's remember-me localStorage keys per project so logging into
    #     one site no longer evicts another's remembered login.
    python3 - "$out_dir" <<'STATICRYPT_GUARD'
import sys, pathlib
root = pathlib.Path(sys.argv[1])
ns = root.parent.parent.name  # project dir name -> per-site localStorage namespace
n = 0
for f in root.rglob("*.html"):
    s = f.read_text(encoding="utf-8")
    if 'id="staticrypt-password"' not in s:
        continue
    s2 = s
    if 'autocomplete="new-password"' not in s2:
        s2 = s2.replace('name="password"', 'name="password" autocomplete="new-password"', 1)
        s2 = s2.replace('<form id="staticrypt-form"', '<form id="staticrypt-form" autocomplete="off"', 1)
    s2 = s2.replace('"staticrypt_passphrase"', '"staticrypt_passphrase_' + ns + '"')
    s2 = s2.replace('"staticrypt_expiration"', '"staticrypt_expiration_' + ns + '"')
    if s2 != s:
        f.write_text(s2, encoding="utf-8"); n += 1
print("  staticrypt-guard: patched " + str(n) + " login page(s) (autofill + remember ns=" + ns + ")")
STATICRYPT_GUARD
    local html_ct non_html_ct
    html_ct=$(find "$out_dir" -type f -name "*.html" | wc -l)
    non_html_ct=$(find "$out_dir" -type f -not -name "*.html" | wc -l)
    echo "  -> build/site-encrypted/ ($html_ct encrypted HTML, $non_html_ct unencrypted assets)"
    echo "  NOTE: non-HTML assets are NOT encrypted -- reachable by direct URL."
}

sk_deploy_site() {
    local gated="${SITE_GATED:-1}" src
    if [[ "$gated" == "1" ]]; then
        src="$PROJECT_DIR/build/site-encrypted"
        [[ -d "$src" ]] || { echo "ERROR: $src does not exist. Run 'bash build.sh encrypt' first."; exit 1; }
        # staticrypt encrypts only HTML; drop any PDF so none is reachable by URL.
        find "$src" -type f -name '*.pdf' -delete
    else
        src="$PROJECT_DIR/build/site"
        [[ -d "$src" ]] || { echo "ERROR: $src does not exist. Run 'bash build.sh site' first."; exit 1; }
    fi
    local repo; repo="$(sk__repo)"
    local url="https://${repo%%/*}.github.io/${repo#*/}/"
    echo ""
    echo "=== Deploying $([[ "$gated" == "1" ]] && echo encrypted || echo PLAINTEXT) site to GitHub Pages ($repo gh-pages) ==="
    local tmp; tmp=$(mktemp -d)
    if git ls-remote --exit-code --heads "git@github.com:$repo.git" gh-pages >/dev/null 2>&1; then
        git clone --quiet --single-branch -b gh-pages "git@github.com:$repo.git" "$tmp"
    else
        echo "  gh-pages branch missing on origin; initialising as orphan."
        git clone --quiet "git@github.com:$repo.git" "$tmp"
        ( cd "$tmp" && git checkout --orphan gh-pages && { git rm -rf --quiet . 2>/dev/null || true; } )
    fi
    rsync -a --delete --exclude='.git' "$src/" "$tmp/"
    printf 'User-agent: *\nDisallow: /\n' > "$tmp/robots.txt"
    ( cd "$tmp"
      git add -A
      if git diff --cached --quiet; then
          echo "  No changes to deploy."
      else
          git commit -m "Deploy site" --quiet
          git push --quiet -u origin gh-pages
          echo "  Deployed -> $url"
      fi )
    rm -rf "$tmp"
}
