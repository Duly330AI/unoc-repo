// Minimal module shims
declare module 'd3';

// Allow importing .vue single-file components under NodeNext/Bundler resolution.
declare module '*.vue' {
    import { DefineComponent } from 'vue'
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, any>
    export default component
}

// Raw import of Vue SFC source (Vite ?raw suffix)
declare module '*.vue?raw' {
    const source: string
    export default source
}
