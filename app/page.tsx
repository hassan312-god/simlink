'use client';
import {useEffect, useState} from 'react';
import Link from 'next/link';
import {
  Home as HomeIcon, LayoutGrid, Library, Search, SlidersHorizontal, Heart, Bell,
  ChevronLeft, ChevronRight, ChevronDown, Play, Download, Gamepad2, Minus, Square, X,
  Bookmark,
} from 'lucide-react';
import {Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription} from '@/components/ui/dialog';
import {games, type Game} from '@/lib/games';
import {cn} from '@/lib/utils';

const order = ['minecraft', 'factorio', 'kerbal', 'flight', 'truck', 'stardew', 'cities'];
const sorted = order.map(id => games.find(g => g.id === id)!).filter(Boolean);
const fastLaunch = sorted.slice(0, 4);
const categories = ['Tous', 'Sandbox', 'Gestion', 'Simulation'];

function readFavorites(): string[] {
  if (typeof window === 'undefined') return [];
  try {
    const stored = JSON.parse(localStorage.getItem('simlink-favorites') || '[]');
    return Array.isArray(stored) ? stored.filter(x => typeof x === 'string' && games.some(g => g.id === x)) : [];
  } catch { return []; }
}

function status(g: Game) {
  return g.ready ? 'CONNECTEUR V0.1' : 'CONCEPT';
}

export default function Home() {
  const [view, setView] = useState<'home' | 'categories' | 'library'>('home');
  const [category, setCategory] = useState('Tous');
  const [query, setQuery] = useState('');
  const [featured, setFeatured] = useState(0);
  const [liked, setLiked] = useState<string[]>(readFavorites);
  const [loaded, setLoaded] = useState(false);
  const [notice, setNotice] = useState(false);

  useEffect(() => {
    // Persist after the first client render; the initial value came from storage.
    if (loaded) try { localStorage.setItem('simlink-favorites', JSON.stringify(liked)); } catch {}
    else queueMicrotask(() => setLoaded(true));
  }, [liked, loaded]);

  const like = (id: string) => setLiked(s => s.includes(id) ? s.filter(x => x !== id) : [...s, id]);
  const hero = sorted[featured];
  const sideLeft = [sorted[(featured + 5) % 7], sorted[(featured + 6) % 7]];
  const sideRight = [sorted[(featured + 1) % 7], sorted[(featured + 2) % 7]];
  const next = () => setFeatured(f => (f + 1) % sorted.length);
  const prev = () => setFeatured(f => (f + sorted.length - 1) % sorted.length);

  const grid = sorted.filter(g =>
    (view !== 'library' || liked.includes(g.id)) &&
    (category === 'Tous' || g.category === category) &&
    g.name.toLowerCase().includes(query.toLowerCase()));
  const rowTitle = view === 'library' ? 'Ma bibliothèque' : view === 'categories' ? 'Catégories' : 'Connecteurs disponibles';

  return (
    <div className="store-bg">
      <div className="store-window">
        <div className="window-controls" aria-hidden="true"><Minus size={13}/><Square size={11}/><X size={13}/></div>

        <aside className="side">
          <Link className="logo" href="/">
            <span className="logo-mark"><Gamepad2 size={20}/></span>
            <span><b>SIMLINK</b><small>GAMESTORE · MCP</small></span>
          </Link>
          <nav className="side-nav" aria-label="Navigation">
            {([['home', 'Accueil', HomeIcon], ['categories', 'Catégories', LayoutGrid], ['library', 'Ma bibliothèque', Library]] as const).map(([id, label, Icon]) => (
              <button key={id} className={cn(view === id && 'active')} onClick={() => { setView(id); setCategory('Tous'); }} aria-current={view === id ? 'page' : undefined}>
                <Icon size={16}/>{label}
              </button>
            ))}
          </nav>
          <span className="side-label">LANCEMENT RAPIDE</span>
          <div className="fast-list">
            {fastLaunch.map(g => (
              <Link key={g.id} href={'/jeux/' + g.id}>
                <img src={g.image} alt="" width={30} height={30}/><span>{g.name}</span>
              </Link>
            ))}
          </div>
          <div className="side-bottom">
            <a className="download-card" href="/install">
              <img src="/games/minecraft-build.webp" alt=""/>
              <div><b>Simlink Local 0.1.0</b><span>Moteur Minecraft · RCON</span>
                <div className="bar"><i style={{width: '68%'}}/></div></div>
              <small>68%</small>
            </a>
          </div>
        </aside>

        <main className="content">
          <header className="topbar">
            <label className="search">
              <Search size={15}/>
              <input placeholder="Rechercher un jeu" value={query} onChange={e => setQuery(e.target.value)} aria-label="Rechercher un jeu"/>
              <SlidersHorizontal size={15}/>
            </label>
            <div className="top-right">
              <button className="icon-btn" aria-label="Favoris" onClick={() => setView('library')}><Heart size={16}/>{liked.length > 0 && <span className="dot">{liked.length}</span>}</button>
              <button className="icon-btn" aria-label="Notifications" onClick={() => setNotice(true)}><Bell size={16}/><span className="dot">1</span></button>
              <a className="profile" href="/install">
                <span className="avatar">S</span>
                <span><b>Simlink Local</b><small>Installer le moteur</small></span>
              </a>
            </div>
          </header>

          {view === 'home' && (
            <section className="carousel" aria-label="À la une">
              {sideLeft.map((g, i) => (
                <button key={g.id} className={cn('fan', i === 0 ? 'fan-far-left' : 'fan-left')} onClick={() => setFeatured(sorted.indexOf(g))} aria-label={'Mettre en avant ' + g.name}>
                  <img src={g.image} alt=""/>
                </button>
              ))}
              <article className="feature" style={{backgroundImage: `url(${hero.image})`}}>
                <div className="feature-shade"/>
                <button className={cn('heart', liked.includes(hero.id) && 'on')} aria-pressed={liked.includes(hero.id)} aria-label="Ajouter aux favoris" onClick={() => like(hero.id)}><Heart size={15}/></button>
                <div className="feature-text">
                  <h1>{hero.name}</h1>
                  <p>{hero.description}</p>
                  <div className="feature-actions">
                    <Link className="pill" href={'/jeux/' + hero.id}>DÉCOUVRIR</Link>
                    <Link className="round" aria-label={'Voir la page de ' + hero.name} href={'/jeux/' + hero.id}><Play size={13} fill="currentColor"/></Link>
                  </div>
                </div>
              </article>
              {sideRight.map((g, i) => (
                <button key={g.id} className={cn('fan', i === 0 ? 'fan-right' : 'fan-far-right')} onClick={() => setFeatured(sorted.indexOf(g))} aria-label={'Mettre en avant ' + g.name}>
                  <img src={g.image} alt=""/>
                </button>
              ))}
            </section>
          )}

          <section className="row-head">
            <h2>{rowTitle}</h2>
            <div className="row-tools">
              {view === 'categories' && categories.map(c => (
                <button key={c} className={cn('chip', category === c && 'chip-on')} onClick={() => setCategory(c)}>{c}</button>
              ))}
              <button className="link" onClick={() => setView(view === 'home' ? 'categories' : 'home')}>{view === 'home' ? 'Voir tout' : 'Accueil'}</button>
              <button className="arrow" aria-label="Précédent" onClick={prev}><ChevronLeft size={14}/></button>
              <button className="arrow" aria-label="Suivant" onClick={next}><ChevronRight size={14}/></button>
            </div>
          </section>

          <section className="cards">
            {grid.map(g => (
              <article key={g.id} className="card">
                <Link className="cover" href={'/jeux/' + g.id} aria-label={'Ouvrir la page de ' + g.name}>
                  <img src={g.image} alt={'Visuel de ' + g.name} loading="lazy"/>
                </Link>
                <span className="tag">{status(g)}</span>
                <div className="card-title">
                  <h3>{g.name}</h3>
                  <button className={cn('mini-heart', liked.includes(g.id) && 'on')} aria-pressed={liked.includes(g.id)} aria-label={'Favori ' + g.name} onClick={() => like(g.id)}><Heart size={13}/></button>
                </div>
                <div className="price">
                  <span className={cn('badge', g.ready ? 'green' : 'blue')}>{g.ready ? 'PRÊT' : 'À VENIR'}</span>
                  <s>{g.tools} outils</s>
                  <b>{g.ready ? 'Gratuit' : 'Concept'}</b>
                </div>
              </article>
            ))}
            {grid.length === 0 && (
              <div className="empty">
                <Bookmark size={22}/>
                <p>{view === 'library' ? 'Aucun favori pour l’instant. Touchez le cœur d’un jeu pour le retrouver ici.' : 'Aucun jeu ne correspond.'}</p>
              </div>
            )}
          </section>
        </main>
      </div>

      <Dialog open={notice} onOpenChange={setNotice}>
        <DialogContent className="store-dialog">
          <DialogHeader><DialogTitle>Simlink Local 0.1.0</DialogTitle><DialogDescription>Première version du moteur Minecraft Java.</DialogDescription></DialogHeader>
          <p className="dialog-copy">Le moteur lit l’état d’un serveur Minecraft Java via RCON et propose des actions que vous approuvez localement. Les visuels des jeux appartiennent à leurs éditeurs ; Simlink est un projet indépendant.</p>
          <a className="pill" href="/install"><Download size={14}/>Voir le guide d’installation</a>
        </DialogContent>
      </Dialog>
    </div>
  );
}
