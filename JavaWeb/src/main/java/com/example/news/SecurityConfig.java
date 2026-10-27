package com.example.news;

import java.util.Map;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.csrf.CsrfToken;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@Configuration
public class SecurityConfig {
    @Bean PasswordEncoder passwordEncoder() { return new BCryptPasswordEncoder(); }

    @Bean UserDetailsService users(PasswordEncoder encoder) {
        String name = System.getenv("NEWS_LOGIN_USER");
        String password = System.getenv("NEWS_LOGIN_PASSWORD");
        if (name == null || name.isBlank() || password == null || password.isBlank())
            throw new IllegalStateException("请设置 NEWS_LOGIN_USER 和 NEWS_LOGIN_PASSWORD");
        return new InMemoryUserDetailsManager(User.withUsername(name).password(encoder.encode(password)).roles("USER").build());
    }

    @Bean SecurityFilterChain security(HttpSecurity http) throws Exception {
        return http.authorizeHttpRequests(auth -> auth
                .requestMatchers("/", "/index.html", "/assets/**", "/api/csrf").permitAll()
                .anyRequest().authenticated())
            .exceptionHandling(e -> e.authenticationEntryPoint((req, res, ex) -> res.sendError(401)))
            .formLogin(form -> form.loginProcessingUrl("/login").permitAll()
                .successHandler((req, res, auth) -> res.setStatus(200))
                .failureHandler((req, res, ex) -> res.sendError(401)))
            .logout(logout -> logout.logoutSuccessHandler((req, res, auth) -> res.setStatus(200)))
            .build();
    }

    @RestController
    static class SessionController {
        @GetMapping("/api/csrf") Map<String, String> csrf(CsrfToken token) {
            return Map.of("header", token.getHeaderName(), "token", token.getToken());
        }
        @GetMapping("/api/auth/me") Map<String, String> current(java.security.Principal principal) {
            return Map.of("name", principal.getName());
        }
    }
}
