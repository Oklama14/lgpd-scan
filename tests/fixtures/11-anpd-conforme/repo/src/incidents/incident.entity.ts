@Entity('incidentes_seguranca')
export class SecurityIncident {
  @Column({ name: 'registro_de_incidente' }) registroDeIncidente: string;
  @Column({ name: 'retencao_minima_anos', default: 5 }) retencaoMinimaAnos: number;
}
