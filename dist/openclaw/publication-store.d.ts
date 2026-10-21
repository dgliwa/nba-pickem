import type { PublicationState } from "./types.js";
export declare class PublicationStore {
    private readonly root;
    constructor(root: string);
    read(reportDate: string): PublicationState;
    write(state: PublicationState): void;
    private path;
}
