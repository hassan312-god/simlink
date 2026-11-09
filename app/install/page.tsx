'use client';
import {useState} from 'react';
import Link from 'next/link';
import {ArrowLeft, ArrowRight, Check, Copy, Download, Gamepad2, ShieldCheck, Terminal, ExternalLink, Plug, Monitor, BookOpen} from 'lucide-react';

const gameSetup = {
  'Minecraft Java': {
    intro: <>Utilisez un serveur <b>Minecraft Java que vous administrez sur ce même ordinateur</b>. Dans son fichier <code>server.properties</code>, renseignez :</>,
    code: 'enable-rcon=true\nrcon.port=25575\nrcon.password=VOTRE_SECRET_LONG_ET_UNIQUE',
    after: 'Remplacez la valeur d’exemple par votre secret, utilisez-le aussi dans la configuration Simlink, puis redémarrez le serveur. Un monde solo sans serveur dédié n’est pas pris en charge.',
    doc: ['https://minecraft.wiki/w/Server.properties', 'Documentation server.properties'],
    tools: ['Lire les joueurs et l’heure', 'Lire position et santé', 'Proposer une heure ou une météo', 'Proposer une téléportation'],
    validated: 'Validé sur un vrai serveur Minecraft 1.21.11.',
  },
  Factorio: {
    intro: <>Lancez votre serveur Factorio (headless ou partie hébergée) avec RCON activé :</>,
    code: 'factorio --start-server ma-partie.zip --rcon-port 27015 --rcon-password VOTRE_SECRET',
    after: 'Les actions passent par /silent-command, ce qui désactive les succès sur la sauvegarde. Simlink le rappelle dans chaque proposition.',
    doc: ['https://wiki.factorio.com/Multiplayer#Dedicated/Headless_server', 'Documentation serveur Factorio'],
    tools: ['Lire joueurs, temps, tick, évolution', 'Lire un joueur', 'Proposer jour / nuit ou pause', 'Proposer un message dans le chat'],
    validated: 'Validé sur un vrai serveur Factorio 2.1.24.',
  },
  'Kerbal Space Program': {
    intro: <>Installez le mod <b>kRPC</b>, puis dans sa fenêtre en jeu créez un serveur « Protobuf over TCP » :</>,
    code: 'Adresse : 127.0.0.1\nPort RPC : 50000\nInstallez Simlink avec l’option --kerbal (ou -Kerbal)',
    after: 'Acceptez la demande de connexion « Simlink » quand kRPC l’affiche. Les gaz et le passage d’étage peuvent détruire le vaisseau : lisez chaque proposition.',
    doc: ['https://krpc.github.io/krpc/', 'Documentation kRPC'],
    tools: ['Lire le vaisseau actif : altitude, vitesse, orbite', 'Proposer un réglage des gaz', 'Proposer SAS on / off', 'Proposer l’étage suivant'],
    validated: 'Validé avec un double de l’API kRPC ; test en jeu encore nécessaire.',
  },
} as const;
type GameName = keyof typeof gameSetup;

export default function Install() {
  const [os, setOs] = useState<'Windows' | 'Linux / macOS'>('Windows');
  const [game, setGame] = useState<GameName>('Minecraft Java');
  const [client, setClient] = useState('Claude Desktop');
  const [copied, setCopied] = useState('');
  const win = os === 'Windows';
  const python = win ? '.\\.venv\\Scripts\\python.exe' : '.venv/bin/python';
  const kerbal = game === 'Kerbal Space Program';
  const installer = win ? `.\\install.ps1${kerbal ? ' -Kerbal' : ''}` : `./install.sh${kerbal ? ' --kerbal' : ''}`;
  const setup = gameSetup[game];

  async function copy(text: string, id: string) {
    try { await navigator.clipboard.writeText(text); setCopied(id); } catch { setCopied('error'); }
  }
  const code = (value: string, id: string) => (
    <div className="installcode"><pre>{value}</pre>
      <button aria-label="Copier la commande" onClick={() => copy(value, id)}>{copied === id ? <Check size={17}/> : <Copy size={17}/>}</button>
    </div>
  );

  return (
    <div className="installpage">
      <header>
        <Link className="brand" href="/"><span className="mark"><Gamepad2 size={23}/></span>simlink</Link>
        <Link className="back" href="/"><ArrowLeft size={15}/>Retour au catalogue</Link>
      </header>
      <main>
        <div className="installhero">
          <span className="eyebrow">SIMLINK LOCAL · V0.2.0</span>
          <h1>Le pont entre votre IA<br/>et vos simulations.</h1>
          <p>Installez le moteur local, connectez Minecraft Java, Factorio ou Kerbal Space Program, et gardez le contrôle sur chaque action. Vos identifiants restent sur votre ordinateur.</p>
          <div className="row">
            <a className="primary" href="/downloads/simlink-local-0.2.0.zip" download><Download size={17}/>Télécharger Simlink Local</a>
            <a className="readguide" href="/downloads/README-simlink.md" download><BookOpen size={16}/>Guide complet</a>
          </div>
          <div className="installfacts">
            <span><Terminal size={15}/>Python 3.10+</span>
            <span><Monitor size={15}/>Windows · Linux · macOS</span>
            <span><ShieldCheck size={15}/>Approbation locale</span>
          </div>
        </div>
        <div className="installnotice">
          <b>Validé sur de vrais serveurs.</b>
          <p>Minecraft Java 1.21.11 et Factorio 2.1.24 ont été pilotés en conditions réelles. Kerbal Space Program reste à vérifier en jeu. Aucun jeu n’est connecté à ce site : le vrai tableau de bord est local.</p>
        </div>
        <div className="installlayout">
          <div>
            <div className="osbar"><span>Votre ordinateur</span>
              <div className="tabs">{(['Windows', 'Linux / macOS'] as const).map(o => <button key={o} onClick={() => setOs(o)} className={os === o ? 'selected' : ''}>{o}</button>)}</div>
            </div>
            <div className="osbar"><span>Votre jeu</span>
              <div className="tabs">{(Object.keys(gameSetup) as GameName[]).map(g => <button key={g} onClick={() => setGame(g)} className={game === g ? 'selected' : ''}>{g}</button>)}</div>
            </div>

            <section className="installstep"><span className="stepnum">01</span><div>
              <h2>Installez le moteur local</h2>
              <p>Téléchargez et décompressez l’archive. Ouvrez {win ? 'PowerShell' : 'un terminal'} dans le dossier qui contient <code>pyproject.toml</code>, puis lancez l’installeur :</p>
              {code(installer, 'install')}
              <p>Il crée un environnement Python, installe le moteur et lance la configuration : choix du jeu, port et, pour RCON, mot de passe en entrée masquée. La configuration est enregistrée dans votre profil utilisateur. Ne saisissez aucun secret sur ce site.</p>
            </div></section>

            <section className="installstep"><span className="stepnum">02</span><div>
              <h2>Préparez {game}</h2>
              <p>{setup.intro}</p>
              {code(setup.code, 'game')}
              <p>{setup.after} Gardez les ports fermés à Internet. Simlink n’installe pas le jeu.</p>
              <a className="doclink" href={setup.doc[0]} target="_blank" rel="noreferrer">{setup.doc[1]} <ExternalLink size={12}/></a>
            </div></section>

            <section className="installstep"><span className="stepnum">03</span><div>
              <h2>Vérifiez la connexion et ouvrez le panneau</h2>
              {code(python + ' -m simlink doctor\n' + python + ' -m simlink dashboard', 'doctor')}
              <p>Le diagnostic affiche l’état réel du jeu. Le panneau s’ouvre dans votre navigateur avec un lien local privé. Gardez ce terminal ouvert.</p>
              <div className="localpreview"><div><span className="previewDot"/>SIMLINK LOCAL</div><h3>Observer → Proposer → Approuver</h3><p>Testez la lecture, proposez une action, puis approuvez-la. La réponse brute du jeu est conservée dans le journal local.</p></div>
            </div></section>

            <section className="installstep"><span className="stepnum">04</span><div>
              <h2>Donnez les outils à votre IA</h2>
              <p>Dans un second terminal, générez la configuration MCP avec des chemins absolus :</p>
              {code(python + ' -m simlink client-config', 'mcp')}
              <div className="tabs clienttabs">{['Claude Desktop', 'Gemini CLI', 'GPT'].map(c => <button key={c} className={client === c ? 'selected' : ''} onClick={() => setClient(c)}>{c}</button>)}</div>
              {client === 'Claude Desktop'
                ? <p>Ajoutez le bloc <code>mcpServers</code> généré à la configuration MCP locale de Claude Desktop, sans remplacer vos autres serveurs, puis redémarrez le client. <a href="https://modelcontextprotocol.io/docs/develop/connect-local-servers" target="_blank" rel="noreferrer">Guide MCP local</a>.</p>
                : client === 'Gemini CLI'
                  ? <p>Ajoutez le bloc généré à <code>mcpServers</code> dans votre fichier <code>settings.json</code> Gemini CLI. <a href="https://geminicli.com/docs/tools/mcp-server/" target="_blank" rel="noreferrer">Guide officiel Gemini CLI</a>.</p>
                  : <p>Ce moteur expose des outils MCP stdio. Pour GPT, il faut un hôte compatible MCP local utilisant un modèle GPT. L’interface web ChatGPT ne peut pas importer directement ce processus local.</p>}
              <div className="prompt"><span>PREMIÈRE DEMANDE À VOTRE IA</span><p>« Observe {game === 'Factorio' ? 'mon usine Factorio' : game === 'Kerbal Space Program' ? 'mon vaisseau dans KSP' : 'mon serveur Minecraft'}. Propose une action, attends mon approbation locale, puis vérifie le résultat. »</p></div>
              <p>Votre client IA reçoit les résultats des outils et peut les transmettre à son fournisseur. Les écritures restent en attente jusqu’à votre validation dans le panneau local.</p>
            </div></section>
          </div>

          <div className="installside">
            <div className="installbox"><Plug size={25}/><h3>{game}</h3>
              <ul>{setup.tools.map(t => <li key={t}>{t}</li>)}<li>Approuver, refuser, suspendre</li></ul>
              <div className="notice">{setup.validated} Pas de personnage autonome, ni de commande libre.</div>
            </div>
            <div className="installbox"><h3>En cas de problème</h3>
              <p><b>Connexion refusée</b><br/>Vérifiez que le jeu ou le serveur tourne, que RCON / kRPC est activé et que le port est correct.</p>
              <p><b>Authentification refusée</b><br/>Le secret local doit correspondre au mot de passe RCON.</p>
              <p><b>Action non confirmée</b><br/>Vérifiez le jeu avant de recommencer : elle a pu être exécutée.</p>
              <a className="doclink" href="/downloads/README-simlink.md" download>Lire le guide complet <ArrowRight size={14}/></a>
            </div>
          </div>
        </div>
        {copied === 'error' && <p role="alert">Copie indisponible : sélectionnez et copiez la commande affichée.</p>}
        <footer><Link className="footerbrand" href="/">simlink</Link><span>Le site distribue le moteur. Le panneau local se connecte au jeu.</span></footer>
      </main>
    </div>
  );
}
