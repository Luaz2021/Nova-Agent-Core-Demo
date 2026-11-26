# GUÍA DE VERSIÓN · PHP 8.4 / 8.5 + Laravel 13

Escribe PHP moderno (tipos estrictos, enums, readonly, atributos) y Laravel 13 (PHP 8.3 como mínimo). Lo que aprendiste suele ser PHP 7/8.0 y Laravel 8-10.

## 1. PHP 8.0-8.3 (ya deberías usarlo siempre)
```php
<?php
declare(strict_types=1);

enum Estado: string { case Activo = 'activo'; case Baja = 'baja';
  public function etiqueta(): string { return match ($this) { self::Activo => 'Activo', self::Baja => 'Dado de baja' }; } }

final readonly class Usuario {                      // clase readonly (8.2)
  public function __construct(public int $id, public string $email, public Estado $estado = Estado::Activo) {}
}
$u = new Usuario(id: 1, email: 'a@b.es');            // argumentos con nombre
$pais = $u?->direccion?->pais;                       // nullsafe
$tipo = match (true) { $edad < 18 => 'menor', default => 'adulto' };
const VERSION = '1.0'; class C { const string NOMBRE = 'x'; }   // constantes tipadas (8.3)
#[\Override] public function guardar(): void {}     // atributo Override (8.3)
```

## 2. PHP 8.4
```php
class Producto {
  // Property hooks: get/set en la propia propiedad (adiós a getters/setters de relleno)
  public string $nombre { set => trim($value); }
  public float $precioConIva { get => $this->precio * 1.21; }
  // Visibilidad asimétrica: se lee desde fuera, solo se escribe dentro
  public private(set) float $precio = 0;
}
$total = new Carrito()->total();                     // new sin paréntesis extra
$primero = array_find($items, fn($i) => $i->stock > 0);
$hay = array_any($items, fn($i) => $i->oferta);      // también array_all, array_find_key
$doc = Dom\HTMLDocument::createFromString($html);    // parser HTML5 real
#[\Deprecated('Usa nuevoMetodo()')] function viejo() {}
```

## 3. PHP 8.5 (noviembre de 2025)
```php
$slug = $titulo |> trim(...) |> strtolower(...) |> fn($s) => str_replace(' ', '-', $s);   // operador pipe
$primero = array_first($lista); $ultimo = array_last($lista);    // null si está vacío
$copia = clone($punto, ['x' => 10]);                // clone with: copia cambiando propiedades (útil con readonly)
#[\NoDiscard] function calcular(): int { ... }      // avisa si se ignora el resultado
```
También: trazas de error en los errores fatales, closures y casts en expresiones constantes, extensión `Uri`.

## 4. Laravel 13 (marzo de 2026)
```php
// Modelo con atributos (opcional, en vez de propiedades $table/$fillable/$hidden)
#[Table('users')]
#[Fillable(['name', 'email'])]
#[Hidden(['password'])]
class User extends Model {
  protected function casts(): array { return ['email_verified_at' => 'datetime', 'estado' => Estado::class]; }   // casts() es un MÉTODO
}

// Rutas y controladores
Route::get('/productos/{producto}', [ProductoController::class, 'show']);   // model binding
Queue::route(ProcesarPodcast::class, connection: 'redis', queue: 'podcasts');
Cache::touch('sesion:123', 3600);                  // alarga la caducidad sin leer el valor
```
- Estructura simplificada desde Laravel 11: sin `Kernel.php` ni casi providers; middleware y excepciones se configuran en `bootstrap/app.php` (`->withMiddleware(...)`, `->withExceptions(...)`).
- `php artisan install:api` para la API; Sanctum para tokens.
- Novedades 13: AI SDK oficial, recursos JSON:API, búsqueda vectorial (`whereVectorSimilarTo`, con PostgreSQL + pgvector).
- Frontend: kits de inicio con React, Vue o Livewire, más Vite y Tailwind 4.
- Tests: Pest por defecto (`it('crea usuario', fn () => ...)`).

## 5. Errores típicos de un modelo con PHP/Laravel viejo
1. Sin `declare(strict_types=1)` ni tipos en parámetros y retornos.
2. Constantes de clase o arrays de strings donde va un `enum`.
3. Getters/setters de relleno (8.4 tiene property hooks).
4. `protected $casts = [...]` → método `casts()`.
5. Registrar middleware en `app/Http/Kernel.php` (ya no existe).
6. `array_filter(...)[0]` para buscar uno → `array_find()`.
7. `reset()`/`end()` para el primero o el último → `array_first()`/`array_last()`.
