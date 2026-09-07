#!/bin/bash
# SEO & site-health verification for the F1 dashboard GitHub Pages site.
# Runs all critical checks in one pass. Use after SEO fixes, GSC troubleshooting,
# or any post-GP update to confirm nothing regressed.
#
# Usage: bash scripts/verify_site_health.sh [BASE_URL]
# Default BASE_URL: https://srx1980.github.io/f1-dashboard/
#
# Exit code 0 = all checks passed, 1 = any check failed.

BASE="${1:-https://srx1980.github.io/f1-dashboard/}"
FAIL=0

check() {
  local label="$1"
  local expected="$2"
  local actual="$3"
  if [ "$expected" = "$actual" ]; then
    echo "  ✓ $label ($actual)"
  else
    echo "  ✗ $label (expected $expected, got $actual)"
    FAIL=1
  fi
}

echo "=== F1 Dashboard Site Health Check ==="
echo "Base URL: $BASE"
echo

# 1. HTTP status checks
echo "--- HTTP Status ---"
for path in "" "sitemap.xml" "robots.txt" ".nojekyll"; do
  code=$(curl -sI -o /dev/null -w "%{http_code}" "${BASE}${path}" 2>/dev/null)
  if [ "$path" = ".nojekyll" ]; then
    check "$path" "200" "$code"
  else
    check "$path" "200" "$code"
  fi
done

# CLAUDE.md / AGENTS.md must NOT be public (404 expected)
code=$(curl -sI -o /dev/null -w "%{http_code}" "${BASE}CLAUDE.md" 2>/dev/null)
check "CLAUDE.md (should 404)" "404" "$code"

code=$(curl -sI -o /dev/null -w "%{http_code}" "${BASE}AGENTS.md" 2>/dev/null)
check "AGENTS.md (should 404)" "404" "$code"

echo
echo "--- SEO Checks ---"

# 2. Single H1 tag
h1_count=$(curl -s "${BASE}" 2>/dev/null | grep -c '<h1')
check "H1 count (must be 1)" "1" "$h1_count"

# 3. Static links to driver/team pages
driver_links=$(curl -s "${BASE}" 2>/dev/null | grep -c 'href="drivers/')
check "Driver static links (must be 22)" "22" "$driver_links"

team_links=$(curl -s "${BASE}" 2>/dev/null | grep -c 'href="teams/')
check "Team static links (must be 11)" "11" "$team_links"

# 4. Sitemap URL count
sitemap_urls=$(curl -s "${BASE}sitemap.xml" 2>/dev/null | grep -c '<loc>')
check "Sitemap URLs (must be 35)" "35" "$sitemap_urls"

# 5. Title and meta description present
title=$(curl -s "${BASE}" 2>/dev/null | grep -o '<title>[^<]*</title>' | head -1)
if [ -n "$title" ]; then
  echo "  ✓ Title present: ${title:0:60}..."
else
  echo "  ✗ Title missing"
  FAIL=1
fi

meta_desc=$(curl -s "${BASE}" 2>/dev/null | grep -o 'meta name="description"' | head -1)
if [ -n "$meta_desc" ]; then
  echo "  ✓ Meta description present"
else
  echo "  ✗ Meta description missing"
  FAIL=1
fi

echo
echo "--- Subpage Checks (sample 5) ---"

# 6. Sample driver/team pages return 200
for page in "drivers/ant.html" "drivers/ham.html" "drivers/ver.html" "teams/mercedes.html" "teams/red-bull-racing.html"; do
  code=$(curl -sI -o /dev/null -w "%{http_code}" "${BASE}${page}" 2>/dev/null)
  check "$page" "200" "$code"
done

echo
echo "--- robots.txt ---"
robots=$(curl -s "${BASE}robots.txt" 2>/dev/null)
if echo "$robots" | grep -q "Sitemap:.*sitemap.xml"; then
  echo "  ✓ robots.txt points to sitemap"
else
  echo "  ✗ robots.txt missing sitemap reference"
  FAIL=1
fi

echo
if [ "$FAIL" = "0" ]; then
  echo "=== ALL CHECKS PASSED ✓ ==="
else
  echo "=== SOME CHECKS FAILED ✗ ==="
fi
exit $FAIL
