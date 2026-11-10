import type {Metadata} from 'next';
import Link from 'next/link';
import {notFound} from 'next/navigation';
import {ArrowLeft, ArrowUpRight, Download, Gamepad2, ShieldCheck, Sparkles} from 'lucide-react';
import {games} from '@/lib/games';
import details from '@/lib/game-details.json';
import {GameGallery} from '@/components/game-gallery';
import {SimlinkLogo} from '@/components/simlink-logo';

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
  const info = details[id as keyof typeof details];
  const related = games.filter(item => item.id !== id && item.category === game.category).slice(0, 3);

  return (
    <div className="detail-shell"><aside className="launcher-side detail-side"><Link href="/" className="launcher-brand"><SimlinkLogo/><span>SIMLINK</span></Link><span className="side-caption">MENU</span><nav className="launcher-nav" aria-label="Navigation principale"><Link href="/">Accueil</Link><Link href="/">Explorer</Link><Link href="/">Ma bibliothèque</Link><Link href="/install">Connecteur local</Link></nav><div className="side-rule"/><span className="side-caption">JEUX DU CATALOGUE</span><nav className="launcher-games" aria-label="Jeux du catalogue">{games.slice(0, 7).map(item => <Link href={`/jeux/${item.id}`} key={item.id} aria-current={item.id === id ? 'page' : undefined}><img src={'cover' in item && typeof item.cover === 'string' ? item.cover : item.image} alt=""/><span>{item.name}</span></Link>)}</nav></aside><main className="game-page">
      <header className="game-topbar">
        <span className="game-topbar-label">Fiche du jeu</span>
        <Link className="game-back" href="/"><ArrowLeft size={16}/> Retour au catalogue</Link>
      </header>

      <section className="detail-presentation" aria-labelledby="game-title">
        <div className="detail-intro">
          <span className={`game-status ${game.ready ? 'ready' : ''}`}>{game.ready ? 'CONNECTEUR DISPONIBLE · V0.1' : 'CONCEPT · À DÉVELOPPER'}</span>
          <h1 id="game-title">{game.name}</h1>
          <p>{info?.shortDescription || game.description}</p>
          <div className="game-hero-actions">
            {game.ready ? <Link className="game-primary" href="/install"><Download size={17}/> Installer Simlink Local</Link> : <a className="game-primary" href={game.source} target="_blank" rel="noreferrer">Voir le jeu officiel <ArrowUpRight size={17}/></a>}
            <a className="game-secondary" href={game.source} target="_blank" rel="noreferrer">Site du jeu <ArrowUpRight size={15}/></a>
          </div>
        </div>
        <GameGallery name={game.name} images={info?.screenshots?.length ? info.screenshots : [game.image]}/>
      </section>

      <div className="game-content">
        <section className="game-main-info">
          <div className="game-heading"><Gamepad2 size={19}/><span>LE JEU</span></div>
          <h2>À propos de {game.name}</h2>
          {info ? <><div className="steam-description">{info.description.split(/\n\s*\n/).slice(0, 9).map((paragraph, index) => <p key={index}>{paragraph}</p>)}</div><a className="steam-source" href={game.source} target="_blank" rel="noreferrer">Voir toutes les informations sur Steam <ArrowUpRight size={15}/></a></> : <p>{game.description}</p>}
          {info?.requirements && <section className="steam-requirements"><h2>Configuration requise pour PC</h2><div><article><h3>Minimum</h3><p>{info.requirements.minimum || 'Non renseignée'}</p></article><article><h3>Recommandée</h3><p>{info.requirements.recommended || 'Non renseignée'}</p></article></div></section>}
          <div className="game-heading connector-heading"><Sparkles size={19}/><span>SIMLINK · CONNECTEUR</span></div>
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
          <dl><div><dt>Studio</dt><dd>{info?.developers.join(', ') || game.studio}</dd></div>{info && <><div><dt>Éditeur</dt><dd>{info.publishers.join(', ') || 'Non renseigné'}</dd></div><div><dt>Sortie</dt><dd>{info.releaseDate || 'Non renseignée'}</dd></div><div><dt>Systèmes</dt><dd>{info.platforms.join(', ') || 'Non renseignés'}</dd></div><div><dt>Genres</dt><dd>{info.genres.join(', ') || game.genre}</dd></div><div><dt>Fonctionnalités</dt><dd>{info.features.join(', ') || 'Non renseignées'}</dd></div><div><dt>Langues</dt><dd>{info.languages || 'Non renseignées'}</dd></div></>}<div><dt>Catégorie</dt><dd>{game.category}</dd></div><div><dt>Outils MCP</dt><dd>{game.tools} {game.ready ? 'implémentés' : 'envisagés'}</dd></div><div><dt>Statut Simlink</dt><dd>{game.ready ? 'Adaptateur local disponible' : 'Concept à développer'}</dd></div></dl>
          {game.ready && <Link className="game-facts-link" href="/install">Guide d’installation <ArrowUpRight size={15}/></Link>}
        </aside>
      </div>

      {related.length > 0 && <section className="game-related"><h2>Dans le même univers</h2><div className="game-related-grid">{related.map(item => <Link href={`/jeux/${item.id}`} key={item.id} className="game-related-card"><img src={item.image} alt=""/><span>{item.name}<small>{item.ready ? 'Connecteur disponible' : 'Concept'}</small></span><ArrowUpRight size={17}/></Link>)}</div></section>}
      <footer className="game-footer"><Link href="/">SIMLINK</Link><span>Un protocole. De nouveaux possibles.</span></footer>
    </main></div>
  );
}
