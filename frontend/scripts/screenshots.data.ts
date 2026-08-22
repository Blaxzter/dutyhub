/**
 * The world the screenshots are taken in.
 *
 * Screenshots used to be captured against whatever the local database happened
 * to hold, which is why every published shot said "[DEMO] Cleanup Crew" and
 * "Auto-generated demo event #4". This file replaces that with a small, plausible
 * parish festival — the same shape in both languages, so `en` and `de` captures
 * differ only by the words on screen.
 *
 * Everything here is fictional. Addresses use `example.org`, which is reserved
 * by RFC 2606 and can never route anywhere real.
 */

export type Locale = 'en' | 'de'

export interface CastMember {
  /** Local part of the seeded address; the domain is added on seeding. */
  handle: string
  name: string
}

export interface TaskSeed {
  key: string
  name: string
  description: string
  location: string
  category: string
  /** Day offsets from the event's first day. */
  days: number[]
  startTime: string
  endTime: string
  shiftMinutes: number
  peoplePerShift: number
  /**
   * Fraction of each shift's places to fill, cycled per shift so the roster
   * shows a believable mix of full, nearly-full, and still-open slots rather
   * than a wall of identical numbers.
   */
  fillPattern: number[]
}

export interface WorldSeed {
  organiser: CastMember
  volunteers: CastMember[]
  event: { name: string; description: string }
  tasks: TaskSeed[]
}

/** Shared across locales so both captures show the same faces and occupancy. */
const CAST: { organiser: CastMember; volunteers: CastMember[] } = {
  organiser: { handle: 'lena.hartmann', name: 'Lena Hartmann' },
  volunteers: [
    { handle: 'jonas.keller', name: 'Jonas Keller' },
    { handle: 'miriam.schaefer', name: 'Miriam Schäfer' },
    { handle: 'david.brandt', name: 'David Brandt' },
    { handle: 'sofia.reinhardt', name: 'Sofia Reinhardt' },
    { handle: 'elias.vogt', name: 'Elias Vogt' },
    { handle: 'hannah.bergmann', name: 'Hannah Bergmann' },
    { handle: 'noah.fischer', name: 'Noah Fischer' },
    { handle: 'clara.jung', name: 'Clara Jung' },
  ],
}

export const WORLD: Record<Locale, WorldSeed> = {
  en: {
    ...CAST,
    event: {
      name: 'St. Michael’s Summer Festival',
      description: 'Five days of music, food, and a lot of willing hands.',
    },
    tasks: [
      {
        key: 'welcome',
        name: 'Welcome Desk',
        description: 'Greet visitors, hand out programmes, and point people to the right place.',
        location: 'Main Entrance',
        category: 'Hospitality',
        days: [0, 1, 2, 3, 4],
        startTime: '09:00',
        endTime: '18:00',
        shiftMinutes: 90,
        peoplePerShift: 2,
        fillPattern: [1, 0.5, 1, 0, 0.5, 1],
      },
      {
        key: 'kitchen',
        name: 'Kitchen & Café',
        description: 'Cake, coffee, and the washing-up that follows.',
        location: 'Parish Hall',
        category: 'Catering',
        days: [0, 1, 2, 3, 4],
        startTime: '10:00',
        endTime: '19:00',
        shiftMinutes: 180,
        peoplePerShift: 4,
        fillPattern: [0.75, 1, 0.5, 1],
      },
      {
        key: 'stage',
        name: 'Stage & Sound',
        description: 'Microphones, cables, and keeping the programme running to time.',
        location: 'Courtyard',
        category: 'Technical',
        days: [1, 2, 3],
        startTime: '14:00',
        endTime: '20:00',
        shiftMinutes: 120,
        peoplePerShift: 2,
        fillPattern: [1, 0.5, 0],
      },
      {
        key: 'kids',
        name: 'Kids’ Corner',
        description: 'Games, face painting, and an eye on the little ones.',
        location: 'Garden',
        category: 'Children',
        days: [1, 2, 3, 4],
        startTime: '11:00',
        endTime: '17:00',
        shiftMinutes: 120,
        peoplePerShift: 3,
        fillPattern: [0.66, 1, 0.33],
      },
      {
        key: 'setup',
        name: 'Set-up & Clear-down',
        description: 'Tables, bunting, and putting it all away again on the last evening.',
        location: 'Whole site',
        category: 'Logistics',
        days: [0, 4],
        startTime: '08:00',
        endTime: '11:00',
        shiftMinutes: 90,
        peoplePerShift: 5,
        fillPattern: [0.8, 0.4],
      },
    ],
  },

  de: {
    ...CAST,
    event: {
      name: 'Gemeindefest St. Michael',
      description: 'Fünf Tage Musik, Essen und viele helfende Hände.',
    },
    tasks: [
      {
        key: 'welcome',
        name: 'Empfang',
        description: 'Gäste begrüßen, Programme verteilen und den Weg weisen.',
        location: 'Haupteingang',
        category: 'Gastgeben',
        days: [0, 1, 2, 3, 4],
        startTime: '09:00',
        endTime: '18:00',
        shiftMinutes: 90,
        peoplePerShift: 2,
        fillPattern: [1, 0.5, 1, 0, 0.5, 1],
      },
      {
        key: 'kitchen',
        name: 'Küche & Café',
        description: 'Kuchen, Kaffee und der Abwasch danach.',
        location: 'Gemeindesaal',
        category: 'Verpflegung',
        days: [0, 1, 2, 3, 4],
        startTime: '10:00',
        endTime: '19:00',
        shiftMinutes: 180,
        peoplePerShift: 4,
        fillPattern: [0.75, 1, 0.5, 1],
      },
      {
        key: 'stage',
        name: 'Bühne & Technik',
        description: 'Mikrofone, Kabel und ein Programm, das pünktlich bleibt.',
        location: 'Innenhof',
        category: 'Technik',
        days: [1, 2, 3],
        startTime: '14:00',
        endTime: '20:00',
        shiftMinutes: 120,
        peoplePerShift: 2,
        fillPattern: [1, 0.5, 0],
      },
      {
        key: 'kids',
        name: 'Kinderecke',
        description: 'Spiele, Kinderschminken und ein Auge auf die Kleinen.',
        location: 'Garten',
        category: 'Kinder',
        days: [1, 2, 3, 4],
        startTime: '11:00',
        endTime: '17:00',
        shiftMinutes: 120,
        peoplePerShift: 3,
        fillPattern: [0.66, 1, 0.33],
      },
      {
        key: 'setup',
        name: 'Auf- und Abbau',
        description: 'Tische, Wimpel und am letzten Abend alles wieder wegräumen.',
        location: 'Gesamtes Gelände',
        category: 'Logistik',
        days: [0, 4],
        startTime: '08:00',
        endTime: '11:00',
        shiftMinutes: 90,
        peoplePerShift: 5,
        fillPattern: [0.8, 0.4],
      },
    ],
  },
}
