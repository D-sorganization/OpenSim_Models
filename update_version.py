with open('VERSION', 'r') as f:
    current_version = f.read().strip()

parts = current_version.split('.')
parts[-1] = str(int(parts[-1]) + 1)
new_version = '.'.join(parts)

with open('VERSION', 'w') as f:
    f.write(new_version + '\n')
