'use client';

import {useState} from 'react';

export function GameGallery({name, images}: {name: string; images: string[]}) {
  const [selected, setSelected] = useState(0);
  if (!images.length) return null;
  return <div className="steam-gallery"><div className="steam-gallery-main"><img src={images[selected]} alt={`Capture ${selected + 1} de ${name}`}/><span>{selected + 1} / {images.length}</span></div><div className="steam-gallery-thumbs">{images.map((image, index) => <button type="button" key={image} aria-label={`Afficher la capture ${index + 1}`} aria-pressed={selected === index} onClick={() => setSelected(index)}><img src={image} alt=""/></button>)}</div></div>;
}
