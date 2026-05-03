/* ==========================================================================
   Good Old Boat 2.0 — interactivity
   - Points of Sail diagram (click / arrow keys, rotates the boat & sail)
   - Boat Anatomy hotspots (hover/focus to update the side card)
   - Glossary live filter
   - ⌘K / Ctrl-K focuses glossary search
   - Sticky nav shadow on scroll
   ========================================================================== */

(() => {
  'use strict';

  /* ----------  POINTS OF SAIL  ---------- */
  const POS = {
    irons: {
      tag: 'IN IRONS',
      title: 'In irons (head to wind)',
      blurb: 'Bow pointed straight at the wind. The sails luff and the boat stops. It happens to everyone — the cure is to back the jib, fall off to one side, and start again. This is why we don\'t aim straight at the wind.',
      angle: '0°', trim: 'Sails luffing', speed: 'Stopped', warn: 'You\'ll drift backward — use the rudder reversed',
      rotation: 0, sail: 'M0 -10 L0 50 Z'
    },
    close: {
      tag: 'CLOSE-HAULED',
      title: 'Close-hauled (beating)',
      blurb: 'As close to the wind as the boat will go and still make headway — about 45° on most cruisers. Sails sheeted in tight. The boat heels, the rig is loaded, and the world feels alive. This is how you sail upwind: zig-zag toward where you want to go.',
      angle: '~45° off bow', trim: 'Sheeted hard in', speed: 'Heeled, working', warn: 'Pinching kills speed — bear away to power up',
      rotation: 45, sail: 'M0 -10 Q-12 18 -4 50 Z'
    },
    beam: {
      tag: 'BEAM REACH',
      title: 'Beam reach',
      blurb: 'Wind on the side of the boat — 90° off the bow. For most cruising sailboats this is the fastest, smoothest, easiest point of sail. Sails out to about half. The boat heels just enough to feel alive.',
      angle: '~90° off bow', trim: 'Half eased', speed: 'Fast & balanced', warn: 'Gusts heel you quickly',
      rotation: 90, sail: 'M0 -10 Q-30 20 -8 50 Z'
    },
    broad: {
      tag: 'BROAD REACH',
      title: 'Broad reach',
      blurb: 'Wind well behind the beam, around 135°. The boat sits up flat, the apparent wind drops, and miles fall behind you. The favorite point of sail of every cruiser who ever lived.',
      angle: '~135° off bow', trim: 'Three-quarters eased', speed: 'Fast, flat, easy', warn: 'Watch for an accidental gybe',
      rotation: 135, sail: 'M0 -10 Q-44 24 -12 50 Z'
    },
    run: {
      tag: 'RUNNING',
      title: 'Running (downwind)',
      blurb: 'Wind dead astern. The boat is balanced on the wind like a leaf. Quiet, but tricky — small steering errors can swing the boom across the boat in a crash gybe. This is why preventers exist.',
      angle: '180° behind', trim: 'Sails fully out', speed: 'Calm but unstable', warn: 'Rig a preventer to lock the boom',
      rotation: 180, sail: 'M0 -10 Q-50 30 -16 50 Z'
    }
  };

  const posOrder = ['irons','close','beam','broad','run','broad','beam','close'];
  let posIndex = 2; // start on beam reach

  const $boat   = document.getElementById('posBoat');
  const $sail   = document.getElementById('posSail');
  const $tag    = document.getElementById('posTag');
  const $title  = document.getElementById('posTitle');
  const $blurb  = document.getElementById('posBlurb');
  const $angle  = document.getElementById('posAngle');
  const $trim   = document.getElementById('posTrim');
  const $speed  = document.getElementById('posSpeed');
  const $warn   = document.getElementById('posWarn');
  const $card   = document.getElementById('posCard');
  const dots    = document.querySelectorAll('.pos-dot');

  function setPOS(key) {
    const data = POS[key];
    if (!data) return;
    $boat.setAttribute('transform', `translate(300 300) rotate(${data.rotation})`);
    $sail.setAttribute('d', data.sail);
    $tag.textContent   = data.tag;
    $title.textContent = data.title;
    $blurb.textContent = data.blurb;
    $angle.textContent = data.angle;
    $trim.textContent  = data.trim;
    $speed.textContent = data.speed;
    $warn.textContent  = data.warn;
    $card.dataset.pos  = key;
    dots.forEach(d => d.classList.toggle('active', d.dataset.pos === key));
  }

  dots.forEach(dot => {
    dot.addEventListener('click', () => {
      const k = dot.dataset.pos;
      setPOS(k);
      posIndex = posOrder.indexOf(k) === -1 ? posIndex : posOrder.indexOf(k);
    });
    dot.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); dot.click(); }
    });
  });

  // arrow-key navigation while POS section is in viewport
  const posSection = document.getElementById('points-of-sail');
  let posInView = false;
  if ('IntersectionObserver' in window && posSection) {
    new IntersectionObserver(([e]) => { posInView = e.isIntersecting; }, { threshold: 0.4 })
      .observe(posSection);
  }
  document.addEventListener('keydown', (e) => {
    if (!posInView) return;
    if (e.key === 'ArrowRight') { posIndex = (posIndex + 1) % posOrder.length; setPOS(posOrder[posIndex]); }
    if (e.key === 'ArrowLeft')  { posIndex = (posIndex - 1 + posOrder.length) % posOrder.length; setPOS(posOrder[posIndex]); }
  });

  setPOS('beam');

  /* ----------  BOAT ANATOMY HOTSPOTS  ---------- */
  const $aTitle = document.getElementById('anatomyTitle');
  const $aBlurb = document.getElementById('anatomyBlurb');
  const spots   = document.querySelectorAll('.spot');

  spots.forEach(spot => {
    const name  = spot.dataset.name;
    const blurb = spot.dataset.blurb;
    const set = () => {
      spots.forEach(s => s.classList.remove('active'));
      spot.classList.add('active');
      $aTitle.textContent = name;
      $aBlurb.textContent = blurb;
    };
    spot.addEventListener('mouseenter', set);
    spot.addEventListener('focus',      set);
    spot.addEventListener('click',      set);
    spot.setAttribute('tabindex', '0');
  });

  /* ----------  GLOSSARY FILTER  ---------- */
  const $gInput = document.getElementById('glossaryInput');
  const $gCount = document.getElementById('glossaryCount');
  const items   = [...document.querySelectorAll('#glossaryList li')];
  const total   = items.length;

  function filterGlossary() {
    const q = $gInput.value.trim().toLowerCase();
    let shown = 0;
    items.forEach(li => {
      const text = li.textContent.toLowerCase();
      const match = !q || text.includes(q);
      li.classList.toggle('hidden', !match);
      if (match) shown++;
    });
    $gCount.textContent = `${shown} of ${total}`;
  }
  if ($gInput) $gInput.addEventListener('input', filterGlossary);

  /* ----------  ⌘K / Ctrl-K → focus glossary search  ---------- */
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      $gInput?.focus();
      $gInput?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  });
  document.getElementById('searchBtn')?.addEventListener('click', () => {
    $gInput?.focus();
    $gInput?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  });

  /* ----------  STICKY NAV SHADOW  ---------- */
  const $nav = document.getElementById('nav');
  const onScroll = () => {
    if (!$nav) return;
    if (window.scrollY > 12) $nav.style.boxShadow = '0 1px 0 rgba(10,31,58,.06), 0 8px 24px rgba(10,31,58,.05)';
    else $nav.style.boxShadow = 'none';
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
})();
