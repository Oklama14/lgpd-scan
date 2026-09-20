@Configuration
public class SecurityConfig {
  @Bean PasswordEncoder encoder() { return NoOpPasswordEncoder.getInstance(); }
}
