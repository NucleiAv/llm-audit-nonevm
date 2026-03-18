// V5: Stale account data after CPI - Instance 2 (PATCHED)
// Fix: reload() both reserve accounts after the CPI before any calculation.

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

    pub fn swap(ctx: Context<SwapAction>, amount_in: u64) -> Result<()> {
        let reserve_a_before = ctx.accounts.reserve_a.amount;
        let reserve_b_before = ctx.accounts.reserve_b.amount;

        let cpi_accounts = Transfer {
            from: ctx.accounts.user_token_in.to_account_info(),
            to: ctx.accounts.reserve_a.to_account_info(),
            authority: ctx.accounts.user.to_account_info(),
        };
        let cpi_ctx = CpiContext::new(ctx.accounts.token_program.to_account_info(), cpi_accounts);
        token::transfer(cpi_ctx, amount_in)?;

        // FIX: reload both reserve accounts to get post-CPI state.
        ctx.accounts.reserve_a.reload()?;
        ctx.accounts.reserve_b.reload()?;

        let k = reserve_a_before
            .checked_mul(reserve_b_before)
            .ok_or(PoolError::Overflow)?;
        let new_reserve_a = ctx.accounts.reserve_a.amount; // fresh post-CPI value
        let amount_out = reserve_b_before.saturating_sub(k / new_reserve_a.max(1));

        ctx.accounts.pool.price = ctx
            .accounts
            .reserve_a
            .amount
            .checked_div(ctx.accounts.reserve_b.amount.max(1))
            .unwrap_or(0);

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

#[error_code]
pub enum PoolError {
    #[msg("Arithmetic overflow")]
    Overflow,
}
