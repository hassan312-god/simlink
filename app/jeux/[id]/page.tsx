import type {Metadata} from 'next';
import Link from 'next/link';
import {notFound} from 'next/navigation';
import {ArrowLeft, ArrowUpRight, Download, Gamepad2, ShieldCheck, Sparkles} from 'lucide-react';
import {games} from '@/lib/games';

export function generateStaticParams() {
  return games.map(game => ({id: game.id}));
}

export async function generateMetadata({params}: {params: Promise<{id: string}>}): Promise<Metadata> {
  const {id} = await params;
  const game = games.find(item => item.id === id);
  return {title: game ? `${game.name} — Simlink` : 'Jeu introuvable — Simlink', description: game?.description};
}

export default async function GamePage({params}: {params: Promise<{id: string}>}) {
  const {id} = await params;
  const game = games.find(item => item.id === id);
  if (!game) notFound();
  const related = games.filter(item => item.id !== id && item.category === game.category).slice(0, 3);

  return (
    <main className="game-page">
      <header className="game-topbar">
        <Link className="game-brand" href="/"><span className="logo-mark"><Gamepad2 size={21}/></span><span>SIMLINK<small>GAMESTORE · MCP</small></span></Link>
        <Link className="game-back" href="/"><ArrowLeft size={16}/> Retour au catalogue</Link>
      </header>

      <section className="game-hero" aria-labelledby="game-title">
        <img className="game-hero-image" src={game.image} alt={`Capture de ${game.name}`}/>
        <div className="game-hero-shade"/>
        <div className="game-hero-content">
          <span className={`game-status ${game.ready ? 'ready' : ''}`}>{game.ready ? 'CONNECTEUR DISPONIBLE · V0.1' : 'CONCEPT · À DÉVELOPPER'}</span>
          <h1 id="game-title">{game.name}</h1>
          <p>{game.description}</p>
          <div className="game-hero-actions">
            {game.ready ? <Link className="game-primary" href="/install"><Download size={17}/> Installer Simlink Local</Link> : <a className="game-primary" href={game.source} target="_blank" rel="noreferrer">Voir le jeu officiel <ArrowUpRight size={17}/></a>}
            <a className="game-secondary" href={game.source} target="_blank" rel="noreferrer">Page officielle <ArrowUpRight size={15}/></a>
          </div>
        </div>
      </section>

      <div className="game-content">
        <section className="game-main-info">
          <div className="game-heading"><Sparkles size={19}/><span>À PROPOS DU CONNECTEUR</span></div>
          <h2>{game.ready ? 'Votre monde, accompagné par une IA.' : 'Un univers à connecter.'}</h2>
          <p>{game.ready
            ? 'Simlink Local relie un serveur Minecraft Java sur votre ordinateur à un client IA compatible MCP. L’assistant peut observer le jeu et proposer des changements ; vous approuvez chaque action depuis un panneau local.'
            : 'Ce jeu figure dans le catalogue comme piste de développement. Simlink ne dispose pas encore de mod ou d’adaptateur opérationnel pour le connecter à une IA. Une intégration demandera une interface autorisée, puis des essais sur le jeu réel.'}</p>
          <div className="game-note"><ShieldCheck size={20}/><span>{game.ready
            ? 'Le protocole RCON et le serveur MCP ont été testés. La validation sur une vraie partie Minecraft et avec votre client IA reste à effectuer.'
            : 'Aucun téléchargement de jeu ou de mod n’est fourni ici. La disponibilité d’un connecteur sera annoncée après son développement et sa validation.'}</span></div>
        </section>
        <aside className="game-facts">
          <h2>Informations</h2>
          <dl><div><dt>Studio</dt><dd>{game.studio}</dd></div><div><dt>Genre</dt><dd>{game.genre}</dd></div><div><dt>Catégorie</dt><dd>{game.category}</dd></div><div><dt>Outils MCP</dt><dd>{game.tools} {game.ready ? 'implémentés' : 'envisagés'}</dd></div><div><dt>Statut</dt><dd>{game.ready ? 'Adaptateur local disponible' : 'Concept à développer'}</dd></div></dl>
          {game.ready && <Link className="game-facts-link" href="/install">Guide d’installation <ArrowUpRight size={15}/></Link>}
        </aside>
      </div>

      {related.length > 0 && <section className="game-related"><h2>Dans le même univers</h2><div className="game-related-grid">{related.map(item => <Link href={`/jeux/${item.id}`} key={item.id} className="game-related-card"><img src={item.image} alt=""/><span>{item.name}<small>{item.ready ? 'Connecteur disponible' : 'Concept'}</small></span><ArrowUpRight size={17}/></Link>)}</div></section>}
      <footer className="game-footer"><Link href="/">SIMLINK</Link><span>Un protocole. De nouveaux possibles.</span></footer>
    </main>
  );
}
