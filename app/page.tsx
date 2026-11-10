'use client';
import {useEffect, useState} from 'react';
import Link from 'next/link';
import {ArrowRight, Bell, Bot, BookOpen, Boxes, ChevronLeft, ChevronRight, Compass, Download, Gamepad2, Heart, Home, Library, Search, ShieldCheck, Sparkles} from 'lucide-react';
import {games, type Game} from '@/lib/games';

const featuredGames = ['minecraft', 'satisfactory', 'flight', 'factorio'].map(id => games.find(g => g.id === id)!).filter(Boolean);
const cover = (g: Game) => 'cover' in g && typeof g.cover === 'string' ? g.cover : g.image;
function storedFavorites(): string[] {
  if (typeof window === 'undefined') return [];
  try { const a = JSON.parse(localStorage.getItem('simlink-favorites') || '[]'); return Array.isArray(a) ? a.filter((id): id is string => typeof id === 'string' && games.some(g => g.id === id)) : []; } catch { return []; }
}

export default function HomePage() {
  const [view, setView] = useState<'home'|'explore'|'library'>('home');
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('Tous');
  const [featured, setFeatured] = useState(0);
  const [favorites, setFavorites] = useState<string[]>(storedFavorites);
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => { setHydrated(true); }, []);
  useEffect(() => { if (hydrated) localStorage.setItem('simlink-favorites', JSON.stringify(favorites)); }, [favorites, hydrated]);
  const toggle = (id: string) => setFavorites(a => a.includes(id) ? a.filter(x => x !== id) : [...a, id]);
  const active = featuredGames[featured];
  const filtered = games.filter(g => (view !== 'library' || favorites.includes(g.id)) && (category === 'Tous' || g.category === category) && (g.name+' '+g.genre+' '+g.studio).toLocaleLowerCase('fr').includes(query.toLocaleLowerCase('fr')));
  return <>
    <div className="desktop-required"><Gamepad2 size={32}/><h1>Simlink sur ordinateur</h1><p>Cette interface est conçue pour un PC ou un ordinateur portable.</p></div>
    <div className="launcher">
      <aside className="launcher-side">
        <Link href="/" className="launcher-brand"><span className="brand-glyph"><Gamepad2 size={21}/></span><span>SIMLINK<small>JEUX · MODS · IA</small></span></Link>
        <span className="side-caption">MENU</span>
        <nav className="launcher-nav" aria-label="Navigation principale">
          <button className={view === 'home' ? 'selected' : ''} onClick={() => {setView('home');setCategory('Tous')}}><Home size={17}/> Accueil</button>
          <button className={view === 'explore' ? 'selected' : ''} onClick={() => setView('explore')}><Compass size={17}/> Explorer</button>
          <button className={view === 'library' ? 'selected' : ''} onClick={() => setView('library')}><Library size={17}/> Ma bibliothèque</button>
          <Link href="/install"><Boxes size={17}/> Connecteur local</Link>
        </nav>
        <div className="side-rule"/><span className="side-caption">JEUX DU CATALOGUE</span>
        <nav className="launcher-games" aria-label="Jeux du catalogue">{games.slice(0,7).map(g => <Link href={'/jeux/'+g.id} key={g.id}><img src={cover(g)} alt=""/><span>{g.name}</span></Link>)}</nav>
        <div className="side-foot"><Link href="/install"><Download size={17}/><span>Simlink Local<small>Installer le moteur Minecraft</small></span><ArrowRight size={15}/></Link></div>
      </aside>
      <div className="launcher-center">
        <header className="launcher-header"><label className="launcher-search"><Search size={18}/><input aria-label="Rechercher un jeu" placeholder="Rechercher un jeu, un studio ou un genre" value={query} onChange={e => setQuery(e.target.value)}/></label><div className="launcher-header-actions"><button aria-label="Afficher mes favoris" onClick={() => setView('library')}><Heart size={18}/></button><Link href="/install" aria-label="Guide Simlink"><BookOpen size={18}/></Link><span className="profile-chip"><span>S</span> Simlink Local</span></div></header>
        <div className="launcher-scroll">
          {view !== 'library' && <section className="launcher-hero" aria-label="Jeu à la une"><img src={active.image} alt=""/><div className="launcher-hero-overlay"/><div className="launcher-hero-copy"><span>{active.ready ? 'CONNECTEUR DISPONIBLE' : 'JEU DU CATALOGUE · CONCEPT'}</span><h1>{active.name}</h1><p>{active.description}</p><Link href={'/jeux/'+active.id}>Découvrir le jeu <ArrowRight size={17}/></Link></div><div className="hero-controls"><button aria-label="Jeu précédent" onClick={() => setFeatured((featured-1+featuredGames.length)%featuredGames.length)}><ChevronLeft size={18}/></button><button aria-label="Jeu suivant" onClick={() => setFeatured((featured+1)%featuredGames.length)}><ChevronRight size={18}/></button></div></section>}
          <section className="launcher-catalog" aria-label="Catalogue des jeux"><div className="catalog-title"><div><span>SIMLINK STORE</span><h2>{view === 'library' ? 'Ma bibliothèque' : 'Découvrez les jeux'}</h2></div><p>{filtered.length} jeu{filtered.length>1?'x':''} · 1 connecteur disponible</p></div>
            <div className="catalog-filters" role="group" aria-label="Catégories">{['Tous','Sandbox','Gestion','Simulation'].map(c => <button key={c} className={category===c?'selected':''} onClick={() => setCategory(c)}>{c}</button>)}</div>
            {filtered.length ? <div className="launcher-grid">{filtered.map(g => <article className="launcher-item" key={g.id}><Link href={'/jeux/'+g.id} className="launcher-poster"><img src={cover(g)} alt={'Visuel de '+g.name} loading="lazy"/></Link><div className="launcher-item-info"><span>{g.genre}</span><button aria-label={(favorites.includes(g.id)?'Retirer des':'Ajouter aux')+' favoris : '+g.name} aria-pressed={favorites.includes(g.id)} onClick={() => toggle(g.id)}><Heart size={16} fill={favorites.includes(g.id)?'currentColor':'none'}/></button></div><Link href={'/jeux/'+g.id} className="launcher-item-name">{g.name}</Link><span className={g.ready?'item-state available':'item-state'}>{g.ready?'Connecteur disponible':'Concept à développer'}</span></article>)}</div> : <div className="catalog-empty"><Search size={22}/><p>{view==='library'?'Aucun favori enregistré.':'Aucun jeu ne correspond.'}</p><button onClick={() => {setView('home');setQuery('');setCategory('Tous')}}>Voir tous les jeux</button></div>}
          </section>
        </div>
      </div>
      <aside className="launcher-rail" aria-label="État des connexions"><div className="rail-heading"><Bot size={19}/> Assistants IA</div><p className="rail-intro">Les clés API et les connexions aux modèles ne sont pas encore configurables dans cette version.</p><div className="provider-list">{['Claude','Gemini','GPT'].map(n => <div key={n}><span className="provider-dot"/><strong>{n}</strong><small>Non configuré</small></div>)}</div><div className="rail-divider"/><div className="rail-heading"><Sparkles size={19}/> Objectifs autonomes</div><p className="rail-intro">La poursuite autonome d’un objectif dans le jeu demande encore un adaptateur de contrôle et des limites d’action.</p><div className="rail-status"><ShieldCheck size={16}/> En développement</div><Link className="rail-action" href="/jeux/minecraft">Voir le premier connecteur <ArrowRight size={15}/></Link><div className="rail-bottom">Simlink ne fournit pas les jeux de ce catalogue.</div></aside>
    </div>
  </>;
}
