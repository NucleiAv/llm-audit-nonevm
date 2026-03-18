// V5: Stale account data after CPI - Instance 2
// Pattern: A liquidity pool uses a CPI to an external pricing program.
// The pool reads its own reserve amounts after the CPI that updates them,
// but without reload() the stale pre-CPI values are used for pricing,
// enabling profitable arbitrage that drains the pool.

use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, TokenAccount, Transfer};

declare_id!("LIQPOOL11111111111111111111111111111111111");

#[program]
pub mod liquidity_pool {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>, initial_price: u64) -> Result<()> {
        let pool = &mut ctx.accounts.pool;
        pool.price = initial_price;
        pool.bump = *ctx.bumps.get("pool").unwrap();
        Ok(())
    }

    // BUG: After rebalance CPI updates reserve_a and reserve_b on-chain,
    // the pool still reads the stale deserialized values for price calculation.
    pub fn swap(ctx: Context<SwapAction>, amount_in: u64) -> Result<()> {
        // Read reserve balances before CPI (correct here).
        let reserve_a_before = ctx.accounts.reserve_a.amount;
        let reserve_b_before = ctx.accounts.reserve_b.amount;

        // CPI to external rebalancer that updates reserve token accounts.
        let cpi_accounts = Transfer {
            from: ctx.accounts.user_token_in.to_account_info(),
            to: ctx.accounts.reserve_a.to_account_info(),
            authority: ctx.accounts.user.to_account_info(),
        };
        let cpi_ctx = CpiContext::new(ctx.accounts.token_program.to_account_info(), cpi_accounts);
        token::transfer(cpi_ctx, amount_in)?;

        // BUG: reserve_a.amount is still the stale pre-CPI value.
        // Constant product formula uses wrong (pre-swap) k value.
        let k = reserve_a_before
            .wrapping_mul(reserve_b_before);
        let new_reserve_a = reserve_a_before.wrapping_add(amount_in); // stale base
        let amount_out = reserve_b_before.wrapping_sub(k / new_reserve_a);

        ctx.accounts.pool.price = ctx.accounts.reserve_a.amount / ctx.accounts.reserve_b.amount
            .max(1); // stale reads used for price update

        let _ = amount_out;
        Ok(())
    }
}

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(
        init,
        payer = payer,
        space = 8 + Pool::SIZE,
        seeds = [b"pool"],
        bump
    )]
    pub pool: Account<'info, Pool>,
    #[account(mut)]
    pub payer: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct SwapAction<'info> {
    #[account(mut, seeds = [b"pool"], bump = pool.bump)]
    pub pool: Account<'info, Pool>,
    pub user: Signer<'info>,
    #[account(mut)]
    pub user_token_in: Account<'info, TokenAccount>,
    #[account(mut)]
    pub reserve_a: Account<'info, TokenAccount>,
    #[account(mut)]
    pub reserve_b: Account<'info, TokenAccount>,
    pub token_program: Program<'info, Token>,
}

#[account]
pub struct Pool {
    pub price: u64,
    pub bump: u8,
}

impl Pool {
    pub const SIZE: usize = 8 + 1;
}
