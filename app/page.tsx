'use client';
import {useEffect, useState} from 'react';
import Link from 'next/link';
import {ArrowRight, Bell, Bot, BookOpen, Boxes, ChevronLeft, ChevronRight, Compass, Download, Gamepad2, Heart, Home, Library, Search, ShieldCheck, Sparkles, Puzzle, Link2, UserRound, Monitor, CalendarDays, Tag} from 'lucide-react';
import {games, type Game} from '@/lib/games';
import {SimlinkLogo} from '@/components/simlink-logo';
import details from '@/lib/game-details.json';

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
        <Link href="/" className="launcher-brand"><SimlinkLogo/><span>SIMLINK</span></Link>
        <span className="side-caption">MENU</span>
        <nav className="launcher-nav" aria-label="Navigation principale">
          <button className={view === 'home' ? 'selected' : ''} onClick={() => {setView('home');setCategory('Tous')}}><Home size={17}/> Accueil</button>
          <button className={view === 'explore' ? 'selected' : ''} onClick={() => setView('explore')}><Compass size={17}/> Explorer</button>
          <button className={view === 'library' ? 'selected' : ''} onClick={() => setView('library')}><Library size={17}/> Ma bibliothèque</button>
          <Link href="/install"><Puzzle size={17}/> Mods</Link>
          <Link href="/install"><Link2 size={17}/> Connecteurs</Link>
        </nav>
        <div className="side-rule"/><span className="side-caption">JEUX À EXPLORER ({games.length})</span>
        <nav className="launcher-games" aria-label="Jeux du catalogue">{games.slice(0,7).map(g => <Link href={'/jeux/'+g.id} key={g.id}><img src={cover(g)} alt=""/><span>{g.name}</span></Link>)}</nav>
        <div className="side-foot"><Link href="/install"><Download size={17}/><span>Simlink Local<small>Installer le moteur Minecraft</small></span><ArrowRight size={15}/></Link></div>
      </aside>
      <div className="launcher-center">
        <header className="launcher-header"><label className="launcher-search"><Search size={18}/><input aria-label="Rechercher un jeu" placeholder="Rechercher un jeu, un mod, un connecteur..." value={query} onChange={e => setQuery(e.target.value)}/><kbd>⌘ K</kbd></label><div className="launcher-header-actions"><button aria-label="Afficher mes favoris" onClick={() => setView('library')}><Heart size={18}/></button><Link href="/install" aria-label="Guide Simlink"><Bell size={18}/></Link><span className="profile-chip"><span><UserRound size={17}/></span> Mon profil <ChevronRight size={14}/></span></div></header>
        <div className="launcher-scroll">
          {view !== 'library' && <section className="launcher-hero" aria-label="Jeu à la une"><img src={active.image} alt=""/><div className="launcher-hero-overlay"/><div className="launcher-hero-copy"><span>{active.ready ? 'CONNECTEUR DISPONIBLE' : 'JEU DU CATALOGUE · CONCEPT'}</span><h1>{active.name}</h1><p>{active.description}</p><Link href={'/jeux/'+active.id}>Découvrir le jeu <ArrowRight size={17}/></Link></div><div className="hero-controls"><button aria-label="Jeu précédent" onClick={() => setFeatured((featured-1+featuredGames.length)%featuredGames.length)}><ChevronLeft size={18}/></button><button aria-label="Jeu suivant" onClick={() => setFeatured((featured+1)%featuredGames.length)}><ChevronRight size={18}/></button></div></section>}
          <section className="launcher-catalog" aria-label="Catalogue des jeux"><div className="catalog-title"><div><h2>{view === 'library' ? 'Ma bibliothèque' : 'Sélection de jeux'}</h2></div><p>{filtered.length} jeu{filtered.length>1?'x':''} · 1 connecteur disponible</p></div>
            <div className="catalog-filters" role="group" aria-label="Catégories">{['Tous','Sandbox','Gestion','Simulation'].map(c => <button key={c} className={category===c?'selected':''} onClick={() => setCategory(c)}>{c}</button>)}</div>
            {filtered.length ? <div className="launcher-grid">{filtered.map(g => <article className="launcher-item" key={g.id}><Link href={'/jeux/'+g.id} className="launcher-poster"><img src={cover(g)} alt={'Visuel de '+g.name} loading="lazy"/></Link><div className="launcher-item-info"><span>{g.genre}</span><button aria-label={(favorites.includes(g.id)?'Retirer des':'Ajouter aux')+' favoris : '+g.name} aria-pressed={favorites.includes(g.id)} onClick={() => toggle(g.id)}><Heart size={16} fill={favorites.includes(g.id)?'currentColor':'none'}/></button></div><Link href={'/jeux/'+g.id} className="launcher-item-name">{g.name}</Link><span className={g.ready?'item-state available':'item-state'}>{g.ready?'Connecteur disponible':'Concept à développer'}</span></article>)}</div> : <div className="catalog-empty"><Search size={22}/><p>{view==='library'?'Aucun favori enregistré.':'Aucun jeu ne correspond.'}</p><button onClick={() => {setView('home');setQuery('');setCategory('Tous')}}>Voir tous les jeux</button></div>}
          </section>
          {view !== 'library' && <section className="launcher-feature-detail" aria-label="Aperçu du jeu à la une"><div className="feature-media"><img src={active.image} alt={`Capture de ${active.name}`}/><div className="feature-thumbs">{(details[active.id as keyof typeof details]?.screenshots || [active.image]).slice(0,4).map((image,index)=><img src={image} alt={`Aperçu ${index+1}`} key={image}/>)}</div></div><div className="feature-copy"><h2>{active.name}</h2><div className="feature-tags"><span>{active.category}</span><span>{active.genre}</span></div><p>{details[active.id as keyof typeof details]?.shortDescription || active.description}</p><dl><div><dt><Boxes size={14}/> Studio</dt><dd>{active.studio}</dd></div><div><dt><Tag size={14}/> Genre</dt><dd>{active.genre}</dd></div><div><dt><Monitor size={14}/> Plateforme</dt><dd>PC</dd></div><div><dt><CalendarDays size={14}/> Statut Simlink</dt><dd>{active.ready ? 'Connecteur disponible' : 'Concept à développer'}</dd></div></dl><Link href={'/jeux/'+active.id}>Voir la fiche complète <ArrowRight size={16}/></Link></div></section>}
        </div>
      </div>
      <aside className="launcher-rail" aria-label="État des connexions"><div className="rail-panel"><div className="rail-heading"><Link2 size={19}/> Fournisseurs IA</div><p className="rail-intro">Connexion et statut des modèles</p><div className="provider-list">{[['OpenAI','GPT'],['Anthropic','Claude'],['Google','Gemini']].map(([brand,name]) => <div key={name}><span className="provider-avatar">{brand[0]}</span><strong>{brand}<small>Non connecté</small></strong><span className="provider-more">···</span></div>)}</div><Link className="rail-action" href="/install"><Link2 size={15}/> Comprendre les connecteurs</Link></div><div className="rail-panel"><div className="rail-heading"><Sparkles size={19}/> Objectif actuel</div><strong className="objective-name">Préparer un connecteur Minecraft</strong><p className="rail-intro">Le connecteur local existe. Le pilotage autonome avec une clé IA est encore en développement.</p><ol className="objective-steps"><li className="done">Connecteur MCP local</li><li>Configurer les permissions</li><li>Ajouter une clé IA</li><li>Tester une mission autonome</li></ol><div className="rail-status"><ShieldCheck size={16}/> En développement</div><Link className="rail-action" href="/jeux/minecraft">Voir Minecraft <ArrowRight size={15}/></Link></div><div className="rail-bottom">Simlink ne fournit pas les jeux de ce catalogue.</div></aside>
    </div>
  </>;
}
