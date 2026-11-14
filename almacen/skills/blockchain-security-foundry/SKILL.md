---
name: blockchain-security-foundry
description: "Estandar oficial de desarrollo, seguridad ofensiva, pruebas de invariantes y auditoria de Smart Contracts con Foundry (Forge, Anvil, Cast) y estandares Cyfrin."
---

# Blockchain Security & Foundry Engineering (Cyfrin Standard)

Estandar tecnico de ingenieria para desarrollo, pruebas exhaustivas y seguridad de Smart Contracts en EVM (Ethereum y Layer 2: Base, Arbitrum, Optimism). Basado en las metodologias de Cyfrin Updraft, Patrick Collins y auditorias de grado institucional.

---

## 1. Tooling Oficial: Foundry First (Cero Hardhat/Ethers v5)

Foundry (`forge`, `cast`, `anvil`) escrito en Rust es el unico ejecutor de compilacion, pruebas y despliegue.

```bash
# Inicializacion y librerias estandar
forge init proyecto_web3
forge install OpenZeppelin/openzeppelin-contracts --no-commit
forge install cyfrin/foundry-devops --no-commit
```

### Comandos de Trinchera
- **Compilacion rapida:** `forge build --sizes` (control estricto del limite de 24 KB de EIP-170).
- **Ejecucion de pruebas con traza detallada:** `forge test -vvvv`
- **Filtro por test especifico:** `forge test --match-test testRevertOnUnauthorized -vvvv`
- **Pruebas contra la red real (Fork):** `forge test --fork-url $RPC_MAINNET -vvvv`
- **Inspeccion de cobertura:** `forge coverage --report lcov`

---

## 2. La Pirámide de Pruebas Obligatoria (Cyfrin Standard)

Toda logica de Smart Contract debe contar con 4 niveles de verificacion antes de considerar produccion:

### A. Pruebas Unitarias & Integracion (`test/unit/`)
Prueban ramas de ejecucion especificas y condiciones de borde:
```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {Test, console} from "forge-std/Test.sol";
import {BovedaRWA} from "../src/BovedaRWA.sol";

contract BovedaRWATest is Test {
    BovedaRWA public boveda;
    address public alice = makeAddr("alice");

    function setUp() public {
        boveda = new BovedaRWA();
        vm.deal(alice, 10 ether);
    }

    function testDepositoIncrementaBalance() public {
        vm.prank(alice);
        boveda.depositar{value: 1 ether}();
        assertEq(boveda.balanceDe(alice), 1 ether);
    }

    function testRevertSiRetiroSinFondos() public {
        vm.prank(alice);
        vm.expectRevert(BovedaRWA.BovedaRWA__FondosInsuficientes.selector);
        boveda.retirar(1 ether);
    }
}
```

### B. Pruebas de Invariantes y Fuzzing (`test/invariants/`)
Las pruebas de invariantes (Stateful Fuzzing) bombardean el contrato con secuencias aleatorias de transacciones para comprobar que las leyes matematicas del negocio NUNCA se rompen:
```solidity
// Invariante: La suma de los balances de los usuarios siempre debe ser menor o igual al balance total del contrato
function invariant_solvenciaTotal() public view {
    assertGe(address(boveda).balance, boveda.totalDepositado());
}
```

---

## 3. Checklist de Auditoría Tanque Web3 (Vulnerabilidades Mortales)

1. **Patrón CEI (Checks - Effects - Interactions):**
   - **Checks:** Validar `require` o errores personalizados primero.
   - **Effects:** Modificar variables de estado internas (balances, mapeos).
   - **Interactions:** Realizar llamadas externas (`call`, transferencias de tokens).
   - *Nunca invertir el orden:* previene el 99% de ataques de reentrancy sin depender unicamente del `nonReentrant`.

2. **Uso de Errores Personalizados (`custom errors`):**
   - Prohibido `require(cond, "mensaje largo")` por coste absurdo de gas.
   - Usar `error Modulo__NombreError();` y revertir con `revert Modulo__NombreError();`.

3. **Oráculos & Manipulación por Flash Loans:**
   - **PROHIBIDO:** Usar `pool.balanceOf()` o el precio spot de un par Uniswap/Sushiswap como oraculo de precio en contratos de prestamo o colateral.
   - **OBLIGATORIO:** Integrar Chainlink Data Feeds (`AggregatorV3Interface`) con validacion de estancamiento (*stale data check*):
   ```solidity
   (, int256 price,, uint256 updatedAt,) = dataFeed.latestRoundData();
   if (updatedAt < block.timestamp - 3600) revert Oraculo__PrecioDesactualizado();
   if (price <= 0) revert Oraculo__PrecioInvalido();
   ```

4. **Aritmética y Precisión:**
   - Multiplicar siempre antes de dividir para no truncar a cero: `uint256 resultado = (monto * tasa) / BASE_DIVISORA;`.
   - Normalizar decimales cuando se interactue con tokens heterogeneos (e.g. USDC con 6 decimales vs DAI/WETH con 18 decimales).

5. **OpenZeppelin 5.x:**
   - Usar `Ownable2Step` en vez de `Ownable` basico para evitar perder la propiedad del contrato por un error tipografico en la direccion de transferencia.
   - Usar `SafeERC20` de OpenZeppelin al interactuar con tokens ERC-20 externos (como USDT que no devuelve booleano en `transfer`).

---

## 4. Auditoría Estática en CI/CD

Antes de cualquier despliegue, validar con linters estaticos a 0 coste:
```bash
# Analisis con Slither
slither . --checklist

# Analisis con Aderyn (Cyfrin)
aderyn .
```

---

## 5. Integración Frontend / Cliente (Stack 2026)
- **Cero `ethers.js v5`:** Es codigo fosil y pesado.
- **Estandar Oficial:** **Viem** (cliente ligero, tipado inferido por ABI) y **Wagmi** (hooks reactivos modernos).
