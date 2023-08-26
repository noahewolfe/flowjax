"""Example tasks"""

import equinox as eqx
import jax
import jax.numpy as jnp
import jax.random as jr
from jax.typing import ArrayLike

from flowjax.distributions import Uniform


def two_moons(key, n_samples, noise_std=0.2):
    """Two moon distribution."""
    angle_key, noise_key = jr.split(key)
    angle = jr.uniform(angle_key, (n_samples,)) * 2 * jnp.pi
    x = 2 * jnp.cos(angle)
    y = 2 * jnp.sin(angle)
    x = jnp.where(angle > jnp.pi, x + 1, x - 1)
    noise = jr.normal(noise_key, (n_samples, 2)) * noise_std
    return jnp.stack([x, y], axis=1) + noise


class GaussianMixtureSimulator:
    r"""Toy simulation based inference task, where the aim is to infer the mean of a
    mixture of two Gaussian distributions, with different variances. Specifically,
    (by default) we have

    .. math::
        \theta_i \sim \text{Uniform}(-10,\ 10), \quad i=1,2
        x | \theta \sim 0.5 \cdot N(\theta,\ I_2) + 0.5 \cdot N(\theta,\ 0.1^2\odot I_2)
    """

    def __init__(self, dim: int = 2, prior_bound: float = 10.0) -> None:
        self.dim = dim
        self.prior_bound = prior_bound
        self.prior = Uniform(-jnp.full(dim, prior_bound), jnp.full(dim, prior_bound))

    @eqx.filter_jit
    def simulator(self, key: jr.KeyArray, theta: ArrayLike):
        theta = jnp.atleast_2d(jnp.asarray(theta))
        key, subkey = jr.split(key)
        component = jr.bernoulli(subkey, shape=(theta.shape[0],))
        scales = self._get_scales(component)

        key, subkey = jr.split(key)
        return (jr.normal(subkey, theta.shape) * scales[:, None] + theta).squeeze()

    def sample_reference_posterior(
        self,
        key: jr.KeyArray,
        observation: ArrayLike,
        num_samples: int,
    ):
        """Sample the reference posterior given an observation. Uses the closed form
        solution with rejection sampling for samples outside prior bound.
        """
        observation = jnp.asarray(observation)
        if observation.shape != (self.dim,):
            raise ValueError(f"Expected shape {(self.dim, )}, got {observation.shape}")

        samples = []
        sample_counter = 0
        while sample_counter < num_samples:
            # Use batches of size num_samples for efficiency
            key, subkey = jr.split(key)

            candidates = jax.jit(jax.vmap(self.simulator, in_axes=[0, None]))(
                jr.split(subkey, num_samples), observation
            )
            in_prior_support = self.prior.log_prob(candidates) != -jnp.inf
            sample_counter += in_prior_support.sum()
            samples.append(candidates[in_prior_support])

        return jnp.concatenate(samples)[:num_samples]

    def _get_scales(self, component):
        return jnp.where(component, 0.1, 1)
