# Logo Files Directory

Place your custom logo files in this directory:

## Required Files:

1. **logo.png** - Main logo (200x60px, transparent PNG)
   - Used on login page and print formats
   
2. **logo-dark.png** - Dark mode version of main logo
   - Used when dark theme is active
   
3. **navbar-logo.png** - Smaller navbar version (150x40px)
   - Displayed in the top navigation bar
   
4. **favicon.ico** - Browser tab icon (32x32px)
   - Shows in browser tabs
   
5. **splash.png** - Loading screen logo (300x100px)
   - Displayed during app loading

## How to Add Your Logos:

1. Create/export your logos in the recommended sizes
2. Save them with the exact filenames listed above
3. Place them in this directory: `apps/api_next/api_next/public/images/`
4. Clear cache and rebuild:
   ```bash
   docker exec devcontainer-frappe-1 bash -c "cd /workspace/frappe-bench && bench build --app api_next && bench clear-cache"
   ```
5. Refresh your browser (Ctrl+F5)

## Design Guidelines:

- Use PNG format with transparent backgrounds
- Keep designs simple and readable at small sizes
- Ensure good contrast for both light and dark backgrounds
- Test logos at different sizes before finalizing

## Optional Files:

- **email-logo.png** - Email header logo (600x150px)
- **print-logo.png** - Print format header (300x100px)
- **mobile-logo.png** - Mobile app logo (512x512px)

Once your logo files are in place, they will automatically be used throughout the application based on the custom CSS configuration.