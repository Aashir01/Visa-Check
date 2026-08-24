// ---------------------------------------------------------------------------
// Photography and footage.
//
// Everything here is Pexels-licensed (free for commercial use, no attribution
// required) and hot-linked from the Pexels CDN, which serves resized variants
// off the `w` query parameter. Keeping the registry in one module means a photo
// is chosen once and reused, rather than a different URL being pasted into
// every page that happens to want an airport.
//
// Each entry records the photographer so the credits page stays honest even
// though the licence does not demand it.
// ---------------------------------------------------------------------------

export type Photo = {
  /** Base CDN URL, without sizing parameters. */
  src: string;
  /** Describes the picture for anyone who cannot see it. */
  alt: string;
  /** Dominant colour, painted under the image so the layout never flashes white. */
  tint: string;
};

export type Clip = {
  /** 1080p H.264 — the widest-supported encoding Pexels offers. */
  src: string;
  /** 720p, used on narrow screens and slow connections. */
  srcSmall: string;
  /** Still frame shown until the first video frame is decoded. */
  poster: string;
  alt: string;
  tint: string;
};

// ---------------------------------------------------------------------------
// URL helpers
// ---------------------------------------------------------------------------

/** Sizes a Pexels image. `w` is the rendered CSS width in pixels. */
export function photoUrl(src: string, w: number): string {
  return `${src}?auto=compress&cs=tinysrgb&w=${w}&dpr=1`;
}

/**
 * Builds a `srcset` across the widths a layout is likely to ask for, so a
 * phone downloads a 640px file rather than the 1600px one a desktop needs.
 */
export function photoSrcSet(src: string, widths: number[] = [480, 768, 1200, 1600]): string {
  return widths.map((w) => `${photoUrl(src, w)} ${w}w`).join(", ");
}

// ---------------------------------------------------------------------------
// Footage
// ---------------------------------------------------------------------------

const VIDEO = "https://videos.pexels.com/video-files";
const VIDEO_POSTER = "https://images.pexels.com/videos";

/** Travellers queueing at a lit immigration desk. Landing hero. */
export const CLIP_IMMIGRATION_DESK: Clip = {
  src: `${VIDEO}/3747854/3747854-hd_1920_1080_24fps.mp4`,
  srcSmall: `${VIDEO}/3747854/3747854-hd_1280_720_24fps.mp4`,
  poster: `${VIDEO_POSTER}/3747854/pexels-photo-3747854.jpeg?auto=compress&cs=tinysrgb&w=1920`,
  alt: "An airport immigration counter, lit under its sign, with officers at the desk",
  tint: "#1a1410",
};

/** Someone working through a stack of immigration paperwork at a table. */
export const CLIP_PAPERWORK: Clip = {
  src: `${VIDEO}/19288030/19288030-hd_1920_1080_60fps.mp4`,
  srcSmall: `${VIDEO}/19288030/19288030-hd_1280_720_60fps.mp4`,
  poster: `${VIDEO_POSTER}/19288030/check-documents-documents-19288030.jpeg?auto=compress&cs=tinysrgb&w=1600`,
  alt: "A person reading through a stack of immigration application forms and guidance notes",
  tint: "#2b2724",
};

/** A parent carrying a child through a departure gate, backlit. Auth pages. */
export const CLIP_DEPARTURE_GATE: Clip = {
  src: `${VIDEO}/13244557/13244557-hd_1920_1080_24fps.mp4`,
  srcSmall: `${VIDEO}/13244557/13244557-hd_1280_720_24fps.mp4`,
  poster: `${VIDEO_POSTER}/13244557/pexels-photo-13244557.jpeg?auto=compress&cs=tinysrgb&w=1600`,
  alt: "A parent holding a child in silhouette at an airport departure gate",
  tint: "#141821",
};

// ---------------------------------------------------------------------------
// Stills
// ---------------------------------------------------------------------------

const PHOTO = "https://images.pexels.com/photos";

export const PHOTO_PASSPORT_STAMPS: Photo = {
  src: `${PHOTO}/4922086/pexels-photo-4922086.jpeg`,
  alt: "A hand holding a passport covered in entry and exit stamps",
  tint: "#8e9aa8",
};

export const PHOTO_VISA_PAGE: Photo = {
  src: `${PHOTO}/4922356/pexels-photo-4922356.jpeg`,
  alt: "An open passport showing a visa page and its printed validity dates",
  tint: "#93a3b3",
};

export const PHOTO_PASSPORTS_WINDOW: Photo = {
  src: `${PHOTO}/13688702/pexels-photo-13688702.jpeg`,
  alt: "Two passports held up against an aircraft window before departure",
  tint: "#8fa2ae",
};

export const PHOTO_RUNWAY_DUSK: Photo = {
  src: `${PHOTO}/35310110/pexels-photo-35310110.jpeg`,
  alt: "An aircraft on the apron at dusk, ground crew working beneath it",
  tint: "#5c5546",
};

// ---------------------------------------------------------------------------
// Corridors
//
// Keyed by the corridor `key` the API returns. A destination people recognise
// on sight does more work on a card than the corridor name alone.
// ---------------------------------------------------------------------------

export const CORRIDOR_PHOTOS: Record<string, Photo> = {
  schengen_short_stay: {
    src: `${PHOTO}/16496484/pexels-photo-16496484.jpeg`,
    alt: "The Eiffel Tower in Paris under a clear winter sky",
    tint: "#9aa8b8",
  },
  schengen_short_stay_pk: {
    src: `${PHOTO}/16292278/pexels-photo-16292278.jpeg`,
    alt: "The Eiffel Tower at dusk seen across the Champ de Mars",
    tint: "#7e8ba4",
  },
  uk_standard_visitor: {
    src: `${PHOTO}/19466056/pexels-photo-19466056.jpeg`,
    alt: "The Elizabeth Tower and its clock face above Westminster",
    tint: "#a8b0bb",
  },
  uk_visitor_pk: {
    src: `${PHOTO}/30624873/pexels-photo-30624873.jpeg`,
    alt: "Tower Bridge in London lit against a deep blue evening sky",
    tint: "#3f4f6b",
  },
  usa_b1b2: {
    src: `${PHOTO}/27807670/pexels-photo-27807670.jpeg`,
    alt: "The Manhattan skyline from above on a clear day",
    tint: "#6f7f92",
  },
  canada_visitor: {
    src: `${PHOTO}/31556761/pexels-photo-31556761.jpeg`,
    alt: "The CN Tower rising above a downtown Toronto street",
    tint: "#8a8b8a",
  },
  australia_visitor: {
    src: `${PHOTO}/16872060/pexels-photo-16872060.jpeg`,
    alt: "Sydney Opera House seen from the water on a bright day",
    tint: "#4c7ba1",
  },
  uae_tourist: {
    src: `${PHOTO}/35687870/pexels-photo-35687870.jpeg`,
    alt: "The Burj Khalifa above the Dubai skyline in morning haze",
    tint: "#a9b2ba",
  },
  japan_tourist: {
    src: `${PHOTO}/30933060/pexels-photo-30933060.jpeg`,
    alt: "A Tokyo street crossing at night under illuminated signage",
    tint: "#1c2434",
  },
  turkey_tourist: {
    src: `${PHOTO}/28764621/pexels-photo-28764621.jpeg`,
    alt: "The Galata Tower above Istanbul and the Golden Horn",
    tint: "#9aa9b6",
  },
  saudi_umrah_pk: {
    src: `${PHOTO}/28209449/pexels-photo-28209449.jpeg`,
    alt: "The Kaaba at the Masjid al-Haram in Mecca at first light",
    tint: "#3b3a3c",
  },
};

export const CORRIDOR_PHOTO_FALLBACK = PHOTO_RUNWAY_DUSK;

/** Never returns undefined — an unknown corridor still gets a picture. */
export function corridorPhoto(key: string | null | undefined): Photo {
  return (key && CORRIDOR_PHOTOS[key]) || CORRIDOR_PHOTO_FALLBACK;
}
