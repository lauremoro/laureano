# Laureano Moro-Velazquez — CV and academic website

This repository contains both the LaTeX CV and a personal academic website. The website is generated from the same `.tex` and `.bib` files and published automatically with GitHub Pages.

## What appears on the website

The public site includes About and research themes, publications, awards and honors, invited talks, and professional service.

Appointments, education, teaching, grants and projects, mentorship, academic committees, and other teaching experience do **not** appear as website sections. Their most relevant information is summarized manually in the About text in `site_config.json`.

## Initial GitHub setup

1. On GitHub, create an empty repository. For the cleanest address, name it `<your-github-username>.github.io`. A different repository name also works, but the address will include that name. Do not add a GitHub-generated README or `.gitignore` when creating it.
2. Extract this package, open a terminal inside the extracted `professor-website` folder, and push it to the repository's `main` branch:

   ```bash
   git init
   git add .
   git commit -m "Create academic website"
   git branch -M main
   git remote add origin https://github.com/lauremoro/laureano.git
   git push -u origin main
   ```

   Replace `YOUR-USERNAME` and `YOUR-REPOSITORY` with the values from GitHub.
3. Open the repository on GitHub and go to **Settings → Pages**.
4. Under **Build and deployment → Source**, select **GitHub Actions**.
5. Open the **Actions** tab. The workflow named **Build CV and publish website** will compile the CV, create the website, and deploy it.
6. When it finishes, the deployment summary will show the public URL.

No deployment command needs to be run on your computer after this setup. Each push to `main` starts the workflow again.

## Updating the site

Edit the existing CV sources as usual:

| Change | Source file |
| --- | --- |
| Name, affiliation, email, Scholar link | `sections/header.tex` |
| Journal articles | `list.bib` |
| Conference papers | `conferences.bib` |
| Awards | `sections/awards.tex` |
| Invited talks | `sections/invited_talks.tex` |
| Professional service | `sections/service.tex` |
| About paragraph, title, research themes, selected papers | `site_config.json` |

Commit and push the changes. GitHub then updates both the PDF and website automatically.

The generator supports the LaTeX patterns already used in this CV: `\cvitem`, `\item`, `\section`, `\subsection`, and the current BibTeX field style. Keep using these patterns for reliable conversion.

## Synchronizing with Overleaf

### If GitHub synchronization is available in your Overleaf plan

Because Overleaf cannot connect an existing Overleaf project to an existing GitHub repository, use one of these starting routes:

- **Keep the current Overleaf project:** In Overleaf, open **Integrations → GitHub** and create a new GitHub repository from that project. Clone the new repository, add the website files from this package, and push them. Back in Overleaf, pull the GitHub changes.
- **Keep the new GitHub repository:** In Overleaf, choose **New Project → Import from GitHub** and select this repository. Use the newly imported Overleaf project going forward.

After linking:

1. Edit the CV in Overleaf.
2. Open **Integrations → GitHub**.
3. Select **Push Overleaf changes to GitHub**.
4. The GitHub Pages workflow starts automatically.

Overleaf synchronization is manual; saving in Overleaf alone does not push to GitHub.

### Without Overleaf GitHub synchronization

Download the updated Overleaf project as a ZIP, replace the corresponding `.tex` and `.bib` files in this repository, commit, and push. Alternatively, edit the source files directly on GitHub or in a local Git clone.

## Previewing locally

Python 3 is the only requirement for the website:

```bash
python tools/build_site.py
python -m http.server 8000 --directory dist
```

Then open `http://localhost:8000`.

To reproduce the downloadable PDF locally, install a TeX distribution with `latexmk` and `biber`, then run:

```bash
latexmk -pdf main.tex
CV_AVAILABLE=1 python tools/build_site.py
cp main.pdf dist/CV_Laureano_Moro-Velazquez.pdf
```

## Optional portrait

Add one image named `profile.jpg`, `profile.jpeg`, `profile.png`, or `profile.webp` to `assets/`. The build will use it automatically. Without an image, the site displays an `LMV` monogram.

For a portrait, use a square image of at least 800 × 800 pixels and keep it below roughly 1 MB.

## Choosing selected publications

The selected papers shown near the top of the Publications section are controlled by `selected_publication_keys` in `site_config.json`. Copy each key from the beginning of the corresponding BibTeX entry:

```json
"selected_publication_keys": [
  "moro2026heyjay",
  "anderson2026weargait"
]
```

If the list is empty, the six newest publications are selected automatically.
