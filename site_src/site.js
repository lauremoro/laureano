const navToggle = document.querySelector('.nav-toggle');
const nav = document.querySelector('.site-nav');
navToggle?.addEventListener('click', () => {
  const open = nav.classList.toggle('open');
  navToggle.setAttribute('aria-expanded', String(open));
});
nav?.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => {
  nav.classList.remove('open');
  navToggle?.setAttribute('aria-expanded', 'false');
}));
const typeFilter = document.querySelector('#type-filter');
const yearFilter = document.querySelector('#year-filter');
const searchInput = document.querySelector('#publication-search');
const cards = [...document.querySelectorAll('#all-publications .publication-card')];
const count = document.querySelector('#publication-count');
const empty = document.querySelector('#no-publications');
function filterPublications() {
  const type = typeFilter?.value ?? 'all';
  const year = yearFilter?.value ?? 'all';
  const query = (searchInput?.value ?? '').trim().toLocaleLowerCase();
  let visible = 0;
  cards.forEach((card) => {
    const show = (type === 'all' || card.dataset.type === type) && (year === 'all' || card.dataset.year === year) && (!query || card.textContent.toLocaleLowerCase().includes(query));
    card.hidden = !show;
    if (show) visible += 1;
  });
  if (count) count.textContent = `${visible} publication${visible === 1 ? '' : 's'}`;
  if (empty) empty.hidden = visible !== 0;
}
[typeFilter, yearFilter, searchInput].forEach((control) => control?.addEventListener('input', filterPublications));
filterPublications();
