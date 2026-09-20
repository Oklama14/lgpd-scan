@Entity('perfis')
export class Profile {
  @Column({ name: 'is_public', default: true }) isPublic: boolean;
  @Column() visibility: string = 'public';
  @Column({ name: 'searchable', default: true }) searchable: boolean;
}
