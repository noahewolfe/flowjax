import pytest
from jax import random
import jax.numpy as jnp
from flowjax.bijections.coupling import Coupling
from flowjax.bijections.masked_autoregressive import MaskedAutoregressive
from flowjax.bijections.parameterised import Affine
from flowjax.bijections.utils import Flip, Permute
from flowjax.bijections.parameterised import Affine, RationalQuadraticSpline

cases1 = {
    "Affine": Affine(),
    "RationalQuadraticSpline": RationalQuadraticSpline(K=5, B=3),
}


@pytest.mark.parametrize("bijection", cases1.values(), ids=cases1.keys())
def test_parameterised_bijection_invertibility(bijection):
    d = 5
    x = random.normal(random.PRNGKey(0), (d,))
    params = random.normal(random.PRNGKey(1), (bijection.num_params(d),))
    args = bijection.get_args(params)
    y = bijection.transform(x, *args)
    x_reconstructed = bijection.inverse(y, *args)

    assert jnp.any(x != y)  # Check change occurs
    assert x == pytest.approx(x_reconstructed, abs=1e-5)


dim = 5
cond_dim = 2
key = random.PRNGKey(0)
cases2 = {
    "Flip": Flip(),
    "Permute": Permute(jnp.flip(jnp.arange(dim))),
    "Coupling (unconditional)": Coupling(
        key,
        Affine(),
        d=dim // 2,
        D=dim,
        cond_dim=0,
        nn_width=10,
        nn_depth=2,
    ),
    "Coupling (conditional)": Coupling(
        key,
        Affine(),
        d=dim // 2,
        D=dim,
        cond_dim=cond_dim,
        nn_width=10,
        nn_depth=2,
    ),
    "MaskedAutoregressive_Affine (unconditional)": MaskedAutoregressive(
        key, Affine(), cond_dim=0, dim=dim, nn_width=10, nn_depth=2
    ),
    "MaskedAutoregressive_Affine (conditional)": MaskedAutoregressive(
        key, Affine(), cond_dim=cond_dim, dim=dim, nn_width=10, nn_depth=2
    ),
    "MaskedAutoregressive_RationalQuadraticSpline (unconditional)": MaskedAutoregressive(
        key, RationalQuadraticSpline(5, 3), cond_dim=0, dim=dim, nn_width=10, nn_depth=2
    ),
    "MaskedAutoregressive_RationalQuadraticSpline (conditional)": MaskedAutoregressive(
        key, RationalQuadraticSpline(5, 3), cond_dim=cond_dim, dim=dim, nn_width=10, nn_depth=2
    )
}


@pytest.mark.parametrize("bijection", cases2.values(), ids=cases2.keys())
def test_bijection_invertibility(bijection):
    x = random.normal(random.PRNGKey(0), (dim,))
    if bijection.cond_dim > 0:
        cond = random.normal(random.PRNGKey(0), (bijection.cond_dim,))
    else:
        cond = None
    y = bijection.transform(x, cond)
    x_reconstructed = bijection.inverse(y, cond)
    assert x == pytest.approx(x_reconstructed, abs=1e-6)