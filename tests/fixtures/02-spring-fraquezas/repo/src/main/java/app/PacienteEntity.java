@Entity
@Table(name = "pacientes")
public class PacienteEntity {
  @Column(name = "cpf") private String cpf;
  @Column(name = "diagnostico") private String diagnostico;
  @Column(name = "tipo_sanguineo") private String tipoSanguineo;
}
