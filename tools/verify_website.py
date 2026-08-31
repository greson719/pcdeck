import glob
import re

site_htmls = glob.glob('website/**/*.html', recursive=True)
print(f'Total HTML files to verify: {len(site_htmls)}')

issues = []

for h in site_htmls:
    with open(h, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check viewport tag
    if 'name="viewport"' not in content and "name='viewport'" not in content:
        issues.append(f'{h}: Missing viewport meta tag')

    # Check nav-toggle if header is present
    if '<header class="top">' in content:
        if 'id="nav-toggle"' not in content:
            issues.append(f'{h}: Missing nav-toggle button in header')
        if 'id="mobile-menu"' not in content:
            issues.append(f'{h}: Missing mobile-menu drawer in header')
        if 'toggle.addEventListener' not in content:
            issues.append(f'{h}: Missing mobile-menu script')

    # Check for unclosed tags
    if content.count('<header') != content.count('</header>'):
        issues.append(f'{h}: Mismatched <header> tags')
    if content.count('<main') != content.count('</main>'):
        issues.append(f'{h}: Mismatched <main> tags')
    if content.count('<footer>') != content.count('</footer>'):
        issues.append(f'{h}: Mismatched <footer> tags')

# Check guide.css
with open('website/guide.css', 'r', encoding='utf-8') as f:
    css = f.read()

for var in ['--accent', '--fg', '--bg', '--paper', '--signal', '--shell']:
    if f'{var}:' not in css:
        issues.append(f'guide.css: Missing definition for {var}')

# Check index.html tokens
with open('website/index.html', 'r', encoding='utf-8') as f:
    index_html = f.read()

for var in ['--accent:', '--fg:', '--bg:', '--paper:', '--signal:']:
    if var not in index_html:
        issues.append(f'index.html: Missing definition for {var}')

# Check no fixed pixel columns wider than 300px
grid_matches = re.findall(r'repeat\(auto-fit,\s*minmax\(([^,]+),', index_html)
for m in grid_matches:
    m = m.strip()
    if m.endswith('px'):
        val = int(m.replace('px', ''))
        if val > 280:
            issues.append(f'index.html: Found grid minmax with hardcoded px > 280px: {m}')

if issues:
    print('ISSUES FOUND:')
    for i in issues:
        print(' -', i)
else:
    print('ALL RESPONSIVENESS AND INTEGRITY CHECKS PASSED!')
